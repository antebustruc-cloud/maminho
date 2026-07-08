"""Phase 3b services — construction projects and season registration."""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from economy.models import InsufficientFundsError, Transaction, move_kc

from . import facility_config
from .models import ConstructionProject, Facility, SeasonRegistration, SportLicense


@transaction.atomic
def start_construction(club, facility_type, *, construction_company=None,
                       security_company=None, construction_price_lc=None,
                       security_price_lc=None):
    """
    Start a construction project for `club`'s facility of `facility_type`.

    - No facility yet → creates it at level 0 and starts a project L0→L1.
    - Facility exists  → starts an upgrade project L→L+1 (max level 7).

    Phase 3c: projects are executed by player-founded companies.
    - `construction_company` must be an active construction company with
      >= required_workers FREE workers; they're assigned for the duration.
    - `security_company` must be an active security company with
      >= required_guards FREE guards; likewise assigned.
    - Prices are freely agreed between the parties (no enforced pricing):
      the club pays construction_price_lc and security_price_lc (integer
      LC) to the respective companies at start, via the ledger.
    Workers/guards free up automatically on completion.
    Returns the ConstructionProject.
    """
    from companies.models import Company, WORKER_TYPE_FOR_COMPANY

    if facility_type not in Facility.FacilityType.values:
        raise ValidationError("Unknown facility_type.")

    facility = club.facilities.filter(facility_type=facility_type).first()
    if facility is None:
        facility = Facility(club=club, facility_type=facility_type, level=0)
        facility.full_clean()
        facility.save()

    if facility.active_project():
        raise ValidationError("This facility already has an active construction project.")
    if facility.level >= Facility.MAX_LEVEL:
        raise ValidationError(f"Facility already at max level ({Facility.MAX_LEVEL}).")

    to_level = facility.level + 1
    config = facility_config.level_config(facility_type, to_level)

    # --- validate company contracts ---
    if not construction_company or not security_company:
        raise ValidationError(
            "construction_company and security_company are required — construction "
            "is carried out by player-founded companies.")
    if (construction_company.company_type != Company.CompanyType.CONSTRUCTION
            or not construction_company.is_active):
        raise ValidationError("Chosen construction company is not an active construction company.")
    if (security_company.company_type != Company.CompanyType.SECURITY
            or not security_company.is_active):
        raise ValidationError("Chosen security company is not an active security company.")

    try:
        construction_price_lc = int(construction_price_lc)
        security_price_lc = int(security_price_lc)
    except (TypeError, ValueError):
        raise ValidationError("construction_price_lc and security_price_lc are required integers (LC).")
    if construction_price_lc < 1 or security_price_lc < 1:
        raise ValidationError("Agreed prices must be positive LC amounts.")

    # Lock free employees to prevent double-assignment under concurrency.
    workers = list(
        construction_company.free_employees(WORKER_TYPE_FOR_COMPANY["construction"])
        .select_for_update()[: config["required_workers"]])
    if len(workers) < config["required_workers"]:
        raise ValidationError(
            f"{construction_company.name} has only {len(workers)} free workers; "
            f"this project needs {config['required_workers']}.")
    guards = list(
        security_company.free_employees(WORKER_TYPE_FOR_COMPANY["security"])
        .select_for_update()[: config["required_guards"]])
    if len(guards) < config["required_guards"]:
        raise ValidationError(
            f"{security_company.name} has only {len(guards)} free guards; "
            f"this project needs {config['required_guards']}.")

    # --- payments: client pays each company its agreed price ---
    try:
        move_kc(from_holder=club, to_holder=construction_company,
                amount=construction_price_lc, kind=Transaction.Kind.CONSTRUCTION,
                description=f"Construction contract: {facility_type} "
                            f"L{facility.level}->L{to_level}")
        move_kc(from_holder=club, to_holder=security_company,
                amount=security_price_lc, kind=Transaction.Kind.CONSTRUCTION,
                description=f"Security contract: {facility_type} "
                            f"L{facility.level}->L{to_level}")
    except InsufficientFundsError as exc:
        raise ValidationError(str(exc))

    now = timezone.now()
    try:
        project = ConstructionProject.objects.create(
            facility=facility,
            from_level=facility.level,
            to_level=to_level,
            status=ConstructionProject.Status.IN_PROGRESS,
            started_at=now,
            ends_at=now + timedelta(days=config["build_time_days"]),
            cost_kc=config["upgrade_cost_kc"],
            required_workers=config["required_workers"],
            required_guards=config["required_guards"],
            is_major=config["is_major"],
            construction_company=construction_company,
            security_company=security_company,
            construction_price_lc=construction_price_lc,
            security_price_lc=security_price_lc,
        )
    except IntegrityError:
        # DB-level guarantee (partial unique constraint) against a racing request.
        raise ValidationError("This facility already has an active construction project.")

    # Assign the crews for the project duration.
    for employee in workers + guards:
        employee.current_project = project
        employee.save(update_fields=["current_project"])
    return project


@transaction.atomic
def register_for_season(club, season):
    """
    Register `club` for `season` (Phase 3b rules):
    - only while the season has not started (status UPCOMING)
    - club must hold a license for the season's sport
    - the sport's mapped facility must exist and be usable
      (a facility mid-major-upgrade blocks registration)
    """
    from .models import Season  # local import to avoid cycles in migrations

    if season.status != Season.Status.UPCOMING:
        raise ValidationError("Registration is only open before the season starts.")
    if SeasonRegistration.objects.filter(club=club, season=season).exists():
        raise ValidationError("Club is already registered for this season.")
    if not club.sport_licenses.filter(sport=season.sport).exists():
        raise ValidationError(f"Club holds no {season.sport} license.")

    required = SportLicense.REQUIRED_FACILITY[season.sport]
    facility = club.facilities.filter(facility_type=required).first()
    if not facility or not facility.is_usable:
        raise ValidationError(
            f"Requires a usable {required} facility. A facility under major "
            "construction is unusable — the club skips this season."
        )

    return SeasonRegistration.objects.create(club=club, season=season, sport=season.sport)
