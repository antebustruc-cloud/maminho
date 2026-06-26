from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Club(models.Model):
    """
    One club per club_owner user, for Phase 1. Holds its own KC balance --
    facility builds/upgrades and license purchases spend from here.
    """

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
    """
    Levels 1-10. Build/upgrade only allowed during offseason -- enforced in
    the serializer/view layer, not here, so this model stays a plain record.
    """

    class FacilityType(models.TextChoices):
        SOCCER_FIELD = "soccer_field", "Soccer field"
        SPORTS_HALL = "sports_hall", "Sports hall"
        SWIMMING_POOL = "swimming_pool", "Swimming pool"
        TENNIS_COURT = "tennis_court", "Tennis court"
        GYM = "gym", "Gym"
        MEDICAL_CENTER = "medical_center", "Medical center"

    # (build_cost, cost_per_level_upgrade)
    COSTS = {
        FacilityType.SOCCER_FIELD: (200, 2000),
        FacilityType.SPORTS_HALL: (3000, 200),
        FacilityType.SWIMMING_POOL: (2000, 200),
        FacilityType.TENNIS_COURT: (100, 200),
        FacilityType.GYM: (1000, 300),
        FacilityType.MEDICAL_CENTER: (1000, 1000),
    }

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="facilities")
    facility_type = models.CharField(max_length=20, choices=FacilityType.choices)
    level = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = ("club", "facility_type")

    def clean(self):
        if not (1 <= self.level <= 10):
            raise ValidationError("Facility level must be between 1 and 10.")
        if self.facility_type == self.FacilityType.MEDICAL_CENTER and self.level >= 5:
            pool = self.club.facilities.filter(
                facility_type=self.FacilityType.SWIMMING_POOL
            ).first()
            if not pool or pool.level < self.level - 1:
                raise ValidationError(
                    "Medical center levels 5-10 require a swimming pool at "
                    "level >= (medical center level - 1)."
                )

    def upgrade_cost(self):
        _, per_level = self.COSTS[self.facility_type]
        return per_level

    def __str__(self):
        return f"{self.club.name} - {self.get_facility_type_display()} (lvl {self.level})"


class SportLicense(models.Model):
    """One license per club per sport. Phase 1 only issues 'football'."""

    class Sport(models.TextChoices):
        FOOTBALL = "football", "Football"
        # Remaining 15 sports added in later phases.

    LICENSE_COSTS = {
        Sport.FOOTBALL: 700,
    }
    REQUIRED_FACILITY = {
        Sport.FOOTBALL: Facility.FacilityType.SOCCER_FIELD,
    }

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="sport_licenses")
    sport = models.CharField(max_length=30, choices=Sport.choices)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("club", "sport")

    def __str__(self):
        return f"{self.club.name} - {self.get_sport_display()} license"
