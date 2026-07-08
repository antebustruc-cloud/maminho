from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError

# ---------------------------------------------------------------------------
# CURRENCY (Phase 3c): 1 KC = 100 LipaCoin (LC), like euros/cents.
# ALL monetary amounts game-wide are stored as integer LC — no floats, no
# Decimal in storage. Legacy field names (kc_balance, amount, cost_kc) were
# kept to avoid a risky rename across the codebase, but their VALUES are LC.
# Use lc_display() whenever an amount is shown to a human.
# ---------------------------------------------------------------------------

LC_PER_KC = 100


def lc_display(amount_lc):
    """Integer LC → human string in KC, e.g. 450 → '4.50 KC'."""
    kc, lipa = divmod(int(amount_lc), LC_PER_KC)
    return f"{kc}.{lipa:02d} KC"


class Transaction(models.Model):
    """
    Every LC movement in the game, ever. This is the source of truth for
    balances -- Club.kc_balance, ManagerProfile.kc_balance and
    Company.kc_balance are cached totals (in LC) that must always equal
    sum(incoming) - sum(outgoing) for that owner. Keeping a full ledger
    means we can always audit/replay the economy.

    The Admin "account" is the central bank: it has infinite LC and isn't
    tracked as a real balance. Transactions to/from it leave the relevant
    side empty (all of from_user/from_company or to_user/to_company null).
    """

    class Kind(models.TextChoices):
        FACILITY_BUILD = "facility_build", "Facility build"
        FACILITY_UPGRADE = "facility_upgrade", "Facility upgrade"
        CONSTRUCTION = "construction", "Facility construction project"
        SPORT_LICENSE = "sport_license", "Sport license purchase"
        BID_WON = "bid_won", "Free agent bid won"
        WAGE_PAYMENT = "wage_payment", "Manager pays player wage"
        CLUB_DEAL_FEE = "club_deal_fee", "Club pays manager monthly fee"
        SIGNING_BONUS = "signing_bonus", "Signing bonus"
        MEDICAL_TREATMENT = "medical_treatment", "Medical treatment fee"
        TOURNAMENT_ENTRY = "tournament_entry", "Tournament entry fee"
        TOURNAMENT_PRIZE = "tournament_prize", "Tournament prize"
        ADMIN_GRANT = "admin_grant", "Admin grant/correction"
        COMPANY_FOUNDING = "company_founding", "Company founding fee"
        DIVIDEND = "dividend", "Company dividend payout"
        NPC_WAGE = "npc_wage", "Company pays NPC workforce wages"
        STAFFING = "staffing", "Recurring facility staffing fee"

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions_sent",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions_received",
    )
    # Company parties (Phase 3c) — companies hold their own balances, so the
    # ledger records them directly rather than through a proxy user.
    from_company = models.ForeignKey(
        "companies.Company",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions_sent",
    )
    to_company = models.ForeignKey(
        "companies.Company",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions_received",
    )
    amount = models.PositiveIntegerField()  # integer LC
    kind = models.CharField(max_length=30, choices=Kind.choices)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def amount_display(self):
        return lc_display(self.amount)

    def __str__(self):
        src = self.from_user or self.from_company or "Bank"
        dst = self.to_user or self.to_company or "Bank"
        return f"{lc_display(self.amount)} [{self.kind}] {src} -> {dst}"


class InsufficientFundsError(ValidationError):
    pass


def _ledger_parties(holder):
    """(user, company) FK values a holder contributes to the Transaction row."""
    if holder is None:
        return None, None
    # Companies are their own ledger party.
    if holder.__class__.__name__ == "Company":
        return None, holder
    # Club → its owner; ManagerProfile → its user.
    user = getattr(holder, "user", None) or getattr(holder, "owner", None)
    return user, None


@transaction.atomic
def move_kc(*, from_holder, to_holder, amount, kind, description=""):
    """
    Moves `amount` (integer LC) between two "holders" and writes a
    Transaction record. Holders are objects with a `kc_balance` field
    holding LC — Club, ManagerProfile, or Company instances — or None for
    the central bank (the Admin's infinite pool).
    """
    if amount <= 0:
        raise ValidationError("Transaction amount must be positive.")

    if from_holder is not None:
        if from_holder.kc_balance < amount:
            raise InsufficientFundsError(
                f"{from_holder} has {lc_display(from_holder.kc_balance)}, "
                f"needs {lc_display(amount)}."
            )
        from_holder.kc_balance -= amount
        from_holder.save(update_fields=["kc_balance"])

    if to_holder is not None:
        to_holder.kc_balance += amount
        to_holder.save(update_fields=["kc_balance"])

    from_user, from_company = _ledger_parties(from_holder)
    to_user, to_company = _ledger_parties(to_holder)
    Transaction.objects.create(
        from_user=from_user,
        to_user=to_user,
        from_company=from_company,
        to_company=to_company,
        amount=amount,
        kind=kind,
        description=description,
    )
