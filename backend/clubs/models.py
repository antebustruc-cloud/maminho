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
        STADIUM        = "stadium",        "Stadium"
        SPORTS_HALL    = "sports_hall",    "Sports hall"
        SWIMMING_POOL  = "swimming_pool",  "Swimming pool"
        TENNIS_COURT   = "tennis_court",   "Tennis court"
        FIGHT_GYM      = "fight_gym",      "Fight gym"
        GYM            = "gym",            "Gym"
        MEDICAL_CENTER = "medical_center", "Medical center"

    # (build_cost, upgrade_cost_per_level) in KC — placeholder values, to be tuned.
    COSTS = {
        FacilityType.STADIUM:        (200,  2000),
        FacilityType.SPORTS_HALL:    (3000,  200),
        FacilityType.SWIMMING_POOL:  (2000,  200),
        FacilityType.TENNIS_COURT:   (100,   200),
        FacilityType.FIGHT_GYM:      (900,   250),
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
        # --- team sports ---
        FOOTBALL      = "football",      "Football"
        FUTSAL        = "futsal",        "Futsal"
        HANDBALL      = "handball",      "Handball"
        BASKETBALL    = "basketball",    "Basketball"
        VOLLEYBALL    = "volleyball",    "Volleyball"
        WATER_POLO    = "water_polo",    "Water polo"
        # --- individual sports ---
        MARATHON      = "marathon",      "Marathon"
        SPRINT_100M   = "sprint_100m",   "Sprint 100m"
        SPRINT_400M   = "sprint_400m",   "Sprint 400m"
        SWIMMING      = "swimming",      "Swimming"
        TENNIS        = "tennis",        "Tennis"
        TABLE_TENNIS  = "table_tennis",  "Table tennis"
        MMA           = "mma",           "MMA"
        BOXING        = "boxing",        "Boxing"
        KICKBOXING    = "kickboxing",    "Kickboxing"
        WRESTLING     = "wrestling",     "Wrestling"
        BJJ           = "bjj",           "Brazilian jiu-jitsu"
        JUDO          = "judo",          "Judo"
        POWERLIFTING  = "powerlifting",  "Powerlifting"
        WEIGHTLIFTING = "weightlifting", "Weightlifting"
        BODYBUILDING  = "bodybuilding",  "Bodybuilding"
        CROSSFIT      = "crossfit",      "CrossFit"

    class SportCategory(models.TextChoices):
        TEAM       = "team",       "Team"
        INDIVIDUAL = "individual", "Individual"

    # Which category each sport belongs to. Other apps should query this
    # via SportLicense.category_for(sport) rather than duplicating the mapping.
    CATEGORY = {
        Sport.FOOTBALL:      SportCategory.TEAM,
        Sport.FUTSAL:        SportCategory.TEAM,
        Sport.HANDBALL:      SportCategory.TEAM,
        Sport.BASKETBALL:    SportCategory.TEAM,
        Sport.VOLLEYBALL:    SportCategory.TEAM,
        Sport.WATER_POLO:    SportCategory.TEAM,
        Sport.MARATHON:      SportCategory.INDIVIDUAL,
        Sport.SPRINT_100M:   SportCategory.INDIVIDUAL,
        Sport.SPRINT_400M:   SportCategory.INDIVIDUAL,
        Sport.SWIMMING:      SportCategory.INDIVIDUAL,
        Sport.TENNIS:        SportCategory.INDIVIDUAL,
        Sport.TABLE_TENNIS:  SportCategory.INDIVIDUAL,
        Sport.MMA:           SportCategory.INDIVIDUAL,
        Sport.BOXING:        SportCategory.INDIVIDUAL,
        Sport.KICKBOXING:    SportCategory.INDIVIDUAL,
        Sport.WRESTLING:     SportCategory.INDIVIDUAL,
        Sport.BJJ:           SportCategory.INDIVIDUAL,
        Sport.JUDO:          SportCategory.INDIVIDUAL,
        Sport.POWERLIFTING:  SportCategory.INDIVIDUAL,
        Sport.WEIGHTLIFTING: SportCategory.INDIVIDUAL,
        Sport.BODYBUILDING:  SportCategory.INDIVIDUAL,
        Sport.CROSSFIT:      SportCategory.INDIVIDUAL,
    }

    # Facility a club must own before it can license the sport.
    REQUIRED_FACILITY = {
        Sport.FOOTBALL:      Facility.FacilityType.STADIUM,
        Sport.FUTSAL:        Facility.FacilityType.SPORTS_HALL,
        Sport.HANDBALL:      Facility.FacilityType.SPORTS_HALL,
        Sport.BASKETBALL:    Facility.FacilityType.SPORTS_HALL,
        Sport.VOLLEYBALL:    Facility.FacilityType.SPORTS_HALL,
        Sport.WATER_POLO:    Facility.FacilityType.SWIMMING_POOL,
        Sport.MARATHON:      Facility.FacilityType.STADIUM,
        Sport.SPRINT_100M:   Facility.FacilityType.STADIUM,
        Sport.SPRINT_400M:   Facility.FacilityType.STADIUM,
        Sport.SWIMMING:      Facility.FacilityType.SWIMMING_POOL,
        Sport.TENNIS:        Facility.FacilityType.TENNIS_COURT,
        Sport.TABLE_TENNIS:  Facility.FacilityType.SPORTS_HALL,
        Sport.MMA:           Facility.FacilityType.FIGHT_GYM,
        Sport.BOXING:        Facility.FacilityType.FIGHT_GYM,
        Sport.KICKBOXING:    Facility.FacilityType.FIGHT_GYM,
        Sport.WRESTLING:     Facility.FacilityType.FIGHT_GYM,
        Sport.BJJ:           Facility.FacilityType.FIGHT_GYM,
        Sport.JUDO:          Facility.FacilityType.FIGHT_GYM,
        Sport.POWERLIFTING:  Facility.FacilityType.GYM,
        Sport.WEIGHTLIFTING: Facility.FacilityType.GYM,
        Sport.BODYBUILDING:  Facility.FacilityType.GYM,
        Sport.CROSSFIT:      Facility.FacilityType.GYM,
    }

    # KC cost per license — placeholder values on football's 700 scale, to be tuned.
    LICENSE_COSTS = {
        Sport.FOOTBALL:      700,
        Sport.FUTSAL:        400,
        Sport.HANDBALL:      450,
        Sport.BASKETBALL:    600,
        Sport.VOLLEYBALL:    450,
        Sport.WATER_POLO:    500,
        Sport.MARATHON:      250,
        Sport.SPRINT_100M:   250,
        Sport.SPRINT_400M:   250,
        Sport.SWIMMING:      300,
        Sport.TENNIS:        400,
        Sport.TABLE_TENNIS:  250,
        Sport.MMA:           400,
        Sport.BOXING:        400,
        Sport.KICKBOXING:    350,
        Sport.WRESTLING:     300,
        Sport.BJJ:           300,
        Sport.JUDO:          300,
        Sport.POWERLIFTING:  250,
        Sport.WEIGHTLIFTING: 250,
        Sport.BODYBUILDING:  250,
        Sport.CROSSFIT:      300,
    }

    @classmethod
    def category_for(cls, sport):
        """Return SportCategory.TEAM or .INDIVIDUAL for a sport value/choice."""
        return cls.CATEGORY[sport]

    club         = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="sport_licenses")
    sport        = models.CharField(max_length=30, choices=Sport.choices)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("club", "sport")

    def __str__(self):
        return f"{self.club.name} – {self.get_sport_display()} license"


class Season(models.Model):
    """
    Controls the global game calendar. Only one season per sport can be
    ACTIVE at a time. Facility builds/upgrades are blocked while a season
    is active. The admin creates seasons via the Django admin.

    GAME TIME: 1 real-world calendar quarter = 1 in-game year. Seasons are
    named after the real quarter they run in ("Q1 2026", "Q2 2026", ...).
    Player ages are plain integers incremented once per quarter at season
    rollover (see the `age_players` management command) — they are NOT
    derived from real dates.
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

    # --- quarterly game-year helpers ---

    @staticmethod
    def quarter_name(date):
        """Canonical season name for a real date, e.g. 'Q3 2026'."""
        quarter = (date.month - 1) // 3 + 1
        return f"Q{quarter} {date.year}"

    @classmethod
    def current_quarter_name(cls):
        from django.utils import timezone
        return cls.quarter_name(timezone.localdate())

    @staticmethod
    def quarter_bounds(date):
        """(start_date, end_date) of the real quarter containing `date`."""
        import calendar
        from datetime import date as date_cls
        first_month = ((date.month - 1) // 3) * 3 + 1
        last_month = first_month + 2
        last_day = calendar.monthrange(date.year, last_month)[1]
        return (date_cls(date.year, first_month, 1),
                date_cls(date.year, last_month, last_day))
