from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError


class Transaction(models.Model):
    """
    Every KC movement in the game, ever. This is the source of truth for
    balances -- Club.kc_balance and ManagerProfile.kc_balance are cached
    totals that must always equal sum(incoming) - sum(outgoing) for that
    owner. Keeping a full ledger means we can always audit/replay the economy.
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

    # from_user / to_user are nullable because the Admin "account" has
    # infinite KC and isn't tracked as a real balance -- transactions to/from
    # Admin are logged with the relevant null side left empty.
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
    amount = models.PositiveIntegerField()
    kind = models.CharField(max_length=30, choices=Kind.choices)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} KC [{self.kind}] {self.from_user} -> {self.to_user}"


class InsufficientFundsError(ValidationError):
    pass


@transaction.atomic
def move_kc(*, from_holder, to_holder, amount, kind, description=""):
    """
    Moves KC between two "holders" (Club or ManagerProfile instances, or None
    for the Admin's infinite pool) and writes a Transaction record.

    from_holder/to_holder are objects with a `kc_balance` IntegerField and a
    `user` FK -- i.e. Club or ManagerProfile. Pass None for Admin.
    """
    if amount <= 0:
        raise ValidationError("Transaction amount must be positive.")

    if from_holder is not None:
        if from_holder.kc_balance < amount:
            raise InsufficientFundsError(
                f"{from_holder} has {from_holder.kc_balance} KC, needs {amount}."
            )
        from_holder.kc_balance -= amount
        from_holder.save(update_fields=["kc_balance"])

    if to_holder is not None:
        to_holder.kc_balance += amount
        to_holder.save(update_fields=["kc_balance"])

    Transaction.objects.create(
        from_user=getattr(from_holder, "user", None) if from_holder else None,
        to_user=getattr(to_holder, "user", None) if to_holder else None,
        amount=amount,
        kind=kind,
        description=description,
    )
