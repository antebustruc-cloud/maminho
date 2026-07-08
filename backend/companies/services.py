"""Phase 3c services — company founding, share transfers, dividends, workforce."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.models import User
from economy.models import InsufficientFundsError, Transaction, lc_display, move_kc

from .models import (
    DEFAULT_WAGES_LC,
    FOUNDING_FEES_LC,
    WORKER_TYPE_FOR_COMPANY,
    Company,
    Employee,
    ShareHolding,
    ShareTransferOffer,
)

OFFER_LIFETIME_HOURS = 48
MIN_EMPLOYMENT_DAYS = 30


def balance_holder_for(user):
    """
    The ledger holder object behind a user: Club for club owners,
    ManagerProfile for managers, None (central bank) for admins.
    """
    if user.role == User.Role.CLUB_OWNER:
        return getattr(user, "club", None)
    if user.role == User.Role.MANAGER:
        return getattr(user, "manager_profile", None)
    return None


@transaction.atomic
def found_company(user, name, company_type):
    """A manager founds a company: pays the founding fee, becomes CEO with
    100% ownership. One company per CEO."""
    if user.role != User.Role.MANAGER:
        raise PermissionDenied("Only managers can found companies.")
    if company_type not in Company.CompanyType.values:
        raise ValidationError("Unknown company_type.")
    if not name:
        raise ValidationError("Company name is required.")
    if Company.objects.filter(ceo=user).exists():
        raise ValidationError("You are already CEO of a company (max one).")
    if Company.objects.filter(name=name).exists():
        raise ValidationError("Company name already taken.")

    fee = FOUNDING_FEES_LC[company_type]
    wallet = balance_holder_for(user)
    try:
        move_kc(from_holder=wallet, to_holder=None, amount=fee,
                kind=Transaction.Kind.COMPANY_FOUNDING,
                description=f"Founded {company_type} company '{name}'")
    except InsufficientFundsError as exc:
        raise ValidationError(str(exc))

    company = Company.objects.create(name=name, company_type=company_type, ceo=user)
    ShareHolding.objects.create(company=company, holder=user, percent=100)
    return company


@transaction.atomic
def create_share_offer(company, from_holder, to_username, percent):
    """Any current holder offers part/all of their percent to another user."""
    percent = int(percent)
    if percent < 1:
        raise ValidationError("percent must be at least 1.")
    holding = ShareHolding.objects.filter(company=company, holder=from_holder).first()
    if not holding or holding.percent < percent:
        raise ValidationError("You don't hold that many shares in this company.")
    to_user = User.objects.filter(username=to_username).first()
    if not to_user:
        raise ValidationError("Unknown recipient username.")
    if to_user == from_holder:
        raise ValidationError("Cannot offer shares to yourself.")

    return ShareTransferOffer.objects.create(
        company=company, from_holder=from_holder, to_user=to_user, percent=percent,
        expires_at=timezone.now() + timedelta(hours=OFFER_LIFETIME_HOURS),
    )


def accept_share_offer(offer, user):
    """Recipient accepts: percent moves, per-company sum stays exactly 100.
    The CEO title never transfers with shares."""
    if offer.to_user != user:
        raise PermissionDenied("This offer isn't addressed to you.")
    if offer.status != ShareTransferOffer.Status.PENDING:
        raise ValidationError(f"Offer is {offer.status}.")
    if offer.expires_at <= timezone.now():
        # Outside the atomic block below on purpose: the expiry marking must
        # persist even though we raise right after.
        offer.status = ShareTransferOffer.Status.EXPIRED
        offer.resolved_at = timezone.now()
        offer.save(update_fields=["status", "resolved_at"])
        raise ValidationError("Offer has expired.")

    with transaction.atomic():
        src = (ShareHolding.objects.select_for_update()
               .filter(company=offer.company, holder=offer.from_holder).first())
        if not src or src.percent < offer.percent:
            raise ValidationError("Offering party no longer holds enough shares.")

        dst, _ = ShareHolding.objects.select_for_update().get_or_create(
            company=offer.company, holder=user, defaults={"percent": 0})

        src.percent -= offer.percent
        dst.percent += offer.percent
        if src.percent == 0:
            src.delete()
        else:
            src.save(update_fields=["percent"])
        dst.save(update_fields=["percent"])

        total = sum(offer.company.holdings.values_list("percent", flat=True))
        assert total == 100, f"Share sum invariant broken: {total}"

        offer.status = ShareTransferOffer.Status.ACCEPTED
        offer.resolved_at = timezone.now()
        offer.save(update_fields=["status", "resolved_at"])
    return offer


@transaction.atomic
def pay_dividend(company, ceo, amount_lc):
    """CEO splits amount_lc from the company account among holders by
    percent, via the ledger. Integer division — any remainder LC stays in
    the company account."""
    if company.ceo != ceo:
        raise PermissionDenied("Only the CEO can pay dividends.")
    amount_lc = int(amount_lc)
    if amount_lc < 1:
        raise ValidationError("Dividend amount must be positive.")
    if company.kc_balance < amount_lc:
        raise ValidationError(
            f"Company has {lc_display(company.kc_balance)}, needs {lc_display(amount_lc)}.")

    payouts = []
    for holding in company.holdings.select_related("holder"):
        share = amount_lc * holding.percent // 100
        if share < 1:
            continue
        move_kc(from_holder=company, to_holder=balance_holder_for(holding.holder),
                amount=share, kind=Transaction.Kind.DIVIDEND,
                description=f"Dividend {holding.percent}% of {lc_display(amount_lc)} "
                            f"from {company.name}")
        payouts.append((holding.holder.username, share))
    return payouts


@transaction.atomic
def hire_employees(company, ceo, count):
    """Instant hiring from the infinite NPC pool — no candidates, just rows.
    Worker type follows the company type; wage is the tunable default."""
    if company.ceo != ceo:
        raise PermissionDenied("Only the CEO can hire.")
    count = int(count)
    if not (1 <= count <= 1000):
        raise ValidationError("count must be between 1 and 1000.")

    worker_type = WORKER_TYPE_FOR_COMPANY[company.company_type]
    wage = DEFAULT_WAGES_LC[worker_type]
    Employee.objects.bulk_create([
        Employee(company=company, worker_type=worker_type, monthly_wage_lc=wage)
        for _ in range(count)
    ])
    return count, worker_type


@transaction.atomic
def fire_employee(company, ceo, employee_id):
    """Firing allowed only after one full month of employment."""
    if company.ceo != ceo:
        raise PermissionDenied("Only the CEO can fire.")
    employee = Employee.objects.filter(id=employee_id, company=company,
                                       fired_at__isnull=True).first()
    if not employee:
        raise ValidationError("No such active employee in your company.")
    if timezone.now() < employee.hired_at + timedelta(days=MIN_EMPLOYMENT_DAYS):
        raise ValidationError("Employees can only be fired after 1 full month of employment.")
    if employee.current_project_id:
        raise ValidationError("Employee is assigned to an active construction project.")

    employee.fired_at = timezone.now()
    employee.save(update_fields=["fired_at"])
    return employee
