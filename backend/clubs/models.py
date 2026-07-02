from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Club(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="club"
    )
    name = models.CharField(max_length=100, unique=True)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    kc_balance = models.PositiveIntegerField(default=5000)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.owner_id and self.owner.role != self.owner.Role.CLUB_OWNER:
            raise ValidationError("Club owner must have the club_owner role.")

    def __str__(self):
        return self.name


class Facility(models.Model):
    class FacilityType(models.TextChoices):
        SOCCER_FIELD   = "soccer_field",   "Soccer field"
        SPORTS_HALL    = "sports_hall",    "Sports hall"
        SWIMMING_POOL  = "swimming_pool",  "Swimming pool"
        TENNIS_COURT   = "tennis_court",   "Tennis court"
        GYM            = "gym",            "Gym"
        MEDICAL_CENTER = "medical_center", "Medical center"

    COSTS = {
        FacilityType.SOCCER_FIELD:   (200,  2000),
        FacilityType.SPORTS_HALL:    (3000,  200),
        FacilityType.SWIMMING_POOL:  (2000,  200),
        FacilityType.TENNIS_COURT:   (100,   200),
        FacilityType.GYM:            (1000,  300),
        FacilityType.MEDICAL_CENTER: (1000, 1000),
    }

    club          = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="facilities")
    facility_type = models.CharField(max_length=20, choices=FacilityType.choices)
    level         = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = ("club", "facility_type")

    def clean(self):
        if not (1 <= self.level <= 10):
            raise ValidationError("Facility level must be between 1 and 10.")
        if self.facility_type == self.FacilityType.MEDICAL_CENTER and self.level >= 5:
            pool = self.club.facilities.filter(facility_type=self.FacilityType.SWIMMING_POOL).first()
            if not pool or pool.level < self.level - 1:
                raise ValidationError(
                    "Medical center levels 5-10 require a swimming pool at level >= (medical_center_level - 1)."
                )

    def upgrade_cost(self):
        _, per_level = self.COSTS[self.facility_type]
        return per_level

    def stat_bonus_pct(self):
        """Level 1 = +1%, level 10 = +10% for monthly player stat growth."""
        return self.level

    def __str__(self):
        return f"{self.club.name} – {self.get_facility_type_display()} (lvl {self.level})"


class SportLicense(models.Model):
    class Sport(models.TextChoices):
        FOOTBALL = "football", "Football"

    LICENSE_COSTS = {Sport.FOOTBALL: 700}
    REQUIRED_FACILITY = {Sport.FOOTBALL: Facility.FacilityType.SOCCER_FIELD}

    club         = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="sport_licenses")
    sport        = models.CharField(max_length=30, choices=Sport.choices)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("club", "sport")

    def __str__(self):
        return f"{self.club.name} – {self.get_sport_display()} license"


class Season(models.Model):
    """
    Controls the global game calendar. Only one season can be ACTIVE at a time.
    Facility builds/upgrades are blocked while a season is active.
    The admin creates seasons via the Django admin.
    """
    class Status(models.TextChoices):
        UPCOMING = "upcoming", "Upcoming"
        ACTIVE   = "active",   "Active"
        FINISHED = "finished", "Finished"

    name       = models.CharField(max_length=100)
    sport      = models.CharField(max_length=30, choices=SportLicense.Sport.choices, default=SportLicense.Sport.FOOTBALL)
    status     = models.CharField(max_length=10, choices=Status.choices, default=Status.UPCOMING)
    start_date = models.DateField()
    end_date   = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.status})"

    @classmethod
    def is_offseason(cls, sport=SportLicense.Sport.FOOTBALL):
        return not cls.objects.filter(sport=sport, status=cls.Status.ACTIVE).exists()
