"""Phase 3b services — construction projects and season registration."""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from economy.models import InsufficientFundsError, Transaction, move_kc

from . import facility_config
from .models import ConstructionProject, Facility, SeasonRegistration, SportLicense


@transaction.atomic
def start_construction(club, facility_type):
    """
    Start a construction project for `club`'s facility of `facility_type`.

    - No facility yet → creates it at level 0 and starts a project L0→L1.
    - Facility exists  → starts an upgrade project L→L+1 (max level 7).

    Validates: one active project per facility, max level, funds.
    Deducts KC immediately via the Transaction ledger (kind=construction).
    Returns the ConstructionProject.
    """
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

    try:
        move_kc(from_holder=club, to_holder=None, amount=config["upgrade_cost_kc"],
                kind=Transaction.Kind.CONSTRUCTION,
                description=f"Construction: {facility_type} L{facility.level}->L{to_level}")
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
        )
    except IntegrityError:
        # DB-level guarantee (partial unique constraint) against a racing request.
        raise ValidationError("This facility already has an active construction project.")
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
