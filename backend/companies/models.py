from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

# All monetary values are integer LC (1 KC = 100 LC). Placeholder values, tunable.

FOUNDING_FEES_LC = {
    "construction": 50000,   # 500 KC
    "security":     30000,   # 300 KC
    "cleaning":     20000,   # 200 KC
}

DEFAULT_WAGES_LC = {
    "construction_worker": 500,   # 5.00 KC / month
    "security_guard":      400,   # 4.00 KC / month
    "cleaner":             300,   # 3.00 KC / month
}

# Which worker type each company type employs.
WORKER_TYPE_FOR_COMPANY = {
    "construction": "construction_worker",
    "security":     "security_guard",
    "cleaning":     "cleaner",
}


class Company(models.Model):
    """
    A player-founded service company (Phase 3c). Founded by a manager-role
    user who becomes CEO with 100% ownership; the CEO title never transfers,
    even if the founder later sells below 50%. Companies hold their own LC
    balance on the ledger: clients pay companies; companies pay NPC wages
    and dividends from this balance.
    """

    class CompanyType(models.TextChoices):
        # Extensible — more types arrive in Phase 3d.
        CONSTRUCTION = "construction", "Construction"
        SECURITY     = "security",     "Security"
        CLEANING     = "cleaning",     "Cleaning"

    name         = models.CharField(max_length=100, unique=True)
    company_type = models.CharField(max_length=20, choices=CompanyType.choices)
    # unique=True → a user can be CEO of at most one company.
    ceo          = models.ForeignKey(settings.AUTH_USER_MODEL, unique=True,
                                     on_delete=models.PROTECT,
                                     related_name="company_as_ceo")
    kc_balance   = models.PositiveIntegerField(default=0)  # integer LC
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "companies"

    def clean(self):
        if self.ceo_id and self.ceo.role != self.ceo.Role.MANAGER:
            raise ValidationError("Company CEO must have the manager role.")

    def free_employees(self, worker_type=None):
        """Active employees not assigned to an active construction project."""
        qs = self.employees.filter(fired_at__isnull=True, current_project__isnull=True,
                                   current_contract__isnull=True)
        if worker_type:
            qs = qs.filter(worker_type=worker_type)
        return qs

    def __str__(self):
        return f"{self.name} ({self.get_company_type_display()})"


class ShareHolding(models.Model):
    """
    A user's ownership slice of a company, in whole percent. Any role may
    hold shares. The sum of percents per company must always equal 100 —
    enforced on founding and on every transfer (see services).
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="holdings")
    holder  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="share_holdings")
    percent = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ("company", "holder")

    def clean(self):
        if not (0 <= self.percent <= 100):
            raise ValidationError("percent must be 0-100.")

    def __str__(self):
        return f"{self.holder} owns {self.percent}% of {self.company.name}"


class ShareTransferOffer(models.Model):
    """
    Consent flow for share transfers: the current holder offers `percent`
    of a company to another user; the recipient accepts or declines.
    Offers expire. No pricing/market — any payment between the two users
    is a normal KC transfer they arrange themselves; accepting just moves
    percent. The CEO title never moves with shares.
    """

    class Status(models.TextChoices):
        PENDING  = "pending",  "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED  = "expired",  "Expired"
        CANCELLED = "cancelled", "Cancelled"

    company     = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="share_offers")
    from_holder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name="share_offers_made")
    to_user     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name="share_offers_received")
    percent     = models.PositiveSmallIntegerField()
    status      = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (f"{self.from_holder} offers {self.percent}% of {self.company.name} "
                f"to {self.to_user} ({self.status})")


class Employee(models.Model):
    """
    NPC workforce (Phase 3c): an infinite labor pool. Hiring is instant and
    unlimited — no candidate generation, the CEO just states how many. Rows
    are cheap; a "worker" is a wage obligation plus an assignment slot.
    Firing is allowed only after one full month of employment.
    """

    class WorkerType(models.TextChoices):
        CONSTRUCTION_WORKER = "construction_worker", "Construction worker"
        SECURITY_GUARD      = "security_guard",      "Security guard"
        CLEANER             = "cleaner",             "Cleaner"

    company         = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="employees")
    worker_type     = models.CharField(max_length=25, choices=WorkerType.choices)
    monthly_wage_lc = models.PositiveIntegerField()  # integer LC
    hired_at        = models.DateTimeField(auto_now_add=True)
    fired_at        = models.DateTimeField(null=True, blank=True)
    # Set while assigned to an active construction project (Phase 3c hook);
    # cleared automatically on project completion.
    current_project = models.ForeignKey("clubs.ConstructionProject", null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name="assigned_employees")
    # Set while assigned to a recurring staffing contract (Phase 3d);
    # cleared when the contract is cancelled.
    current_contract = models.ForeignKey("clubs.FacilityStaffingContract", null=True,
                                         blank=True, on_delete=models.SET_NULL,
                                         related_name="assigned_employees")

    @property
    def is_active(self):
        return self.fired_at is None

    def __str__(self):
        assigned = self.current_project_id or self.current_contract_id
        state = "fired" if self.fired_at else ("assigned" if assigned else "free")
        return f"{self.get_worker_type_display()} @ {self.company.name} ({state})"
