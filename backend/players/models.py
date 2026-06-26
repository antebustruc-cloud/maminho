import random
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from clubs.models import Club, SportLicense
from economy.models import move_kc

STAT = (MinValueValidator(1), MaxValueValidator(30))


class ManagerProfile(models.Model):
    """A manager's wallet + identity. One per manager-role user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="manager_profile"
    )
    kc_balance = models.PositiveIntegerField(default=1000)

    def clean(self):
        if self.user_id and self.user.role != self.user.Role.MANAGER:
            raise ValidationError("ManagerProfile.user must have the manager role.")

    def __str__(self):
        return f"{self.user.username} (manager)"


class Player(models.Model):
    """
    A single player. Phase 1 only generates football players, but the
    schema is shaped to extend to other sports (sport-specific attributes
    will move to a separate per-sport attribute model once we add sport #2,
    to avoid 100+ nullable columns on this table).
    """

    class TalentType(models.TextChoices):
        EARLY_PEAK = "early_peak", "Early peak"
        TALENTED = "talented", "Talented"
        NORMAL = "normal", "Normal"
        LATE_PEAK = "late_peak", "Late peak"

    name = models.CharField(max_length=100)
    sport = models.CharField(max_length=30, default=SportLicense.Sport.FOOTBALL)
    age = models.PositiveSmallIntegerField()
    height_cm = models.PositiveSmallIntegerField()
    weight_kg = models.PositiveSmallIntegerField()
    country = models.CharField(max_length=100)

    # Hidden from API responses to managers/club owners -- visible only via
    # the admin site. Drives monthly stat growth/decline.
    talent_type = models.CharField(max_length=20, choices=TalentType.choices)

    # --- physical attributes (1-30) ---
    agility = models.PositiveSmallIntegerField(validators=STAT)
    strength = models.PositiveSmallIntegerField(validators=STAT)
    speed = models.PositiveSmallIntegerField(validators=STAT)
    acceleration = models.PositiveSmallIntegerField(validators=STAT)
    jump = models.PositiveSmallIntegerField(validators=STAT)
    stamina = models.PositiveSmallIntegerField(validators=STAT)
    injury_resistance = models.PositiveSmallIntegerField(validators=STAT)
    flexibility = models.PositiveSmallIntegerField(validators=STAT)

    # --- mental attributes (1-30), all hidden from non-owners in the API ---
    aggression = models.PositiveSmallIntegerField(validators=STAT)
    bravery = models.PositiveSmallIntegerField(validators=STAT)
    composure = models.PositiveSmallIntegerField(validators=STAT)
    work_rate = models.PositiveSmallIntegerField(validators=STAT)
    team_spirit = models.PositiveSmallIntegerField(validators=STAT)
    influence = models.PositiveSmallIntegerField(validators=STAT)

    # --- football-specific attributes (1-30) ---
    finishing = models.PositiveSmallIntegerField(validators=STAT)
    passing = models.PositiveSmallIntegerField(validators=STAT)
    dribbling = models.PositiveSmallIntegerField(validators=STAT)
    first_touch = models.PositiveSmallIntegerField(validators=STAT)
    crossing = models.PositiveSmallIntegerField(validators=STAT)
    tackling = models.PositiveSmallIntegerField(validators=STAT)
    marking = models.PositiveSmallIntegerField(validators=STAT)
    positioning = models.PositiveSmallIntegerField(validators=STAT)
    off_the_ball = models.PositiveSmallIntegerField(validators=STAT)
    vision = models.PositiveSmallIntegerField(validators=STAT)

    # --- ownership / status ---
    is_free_agent = models.BooleanField(default=True)
    is_starter_player = models.BooleanField(
        default=False, help_text="Starter players (all stats=1) can't be traded, only deleted."
    )
    current_manager = models.ForeignKey(
        ManagerProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="players"
    )
    current_club = models.ForeignKey(
        Club, null=True, blank=True, on_delete=models.SET_NULL, related_name="squad"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.sport}, age {self.age})"

    @staticmethod
    def random_stat():
        """70% land in 1-10, 25% in 11-20, 5% in 21-30, per the design doc."""
        roll = random.random()
        if roll < 0.70:
            return random.randint(1, 10)
        elif roll < 0.95:
            return random.randint(11, 20)
        return random.randint(21, 30)

    @staticmethod
    def random_age():
        roll = random.random()
        if roll < 0.40:
            return random.randint(16, 21)
        elif roll < 0.70:
            return random.randint(22, 25)
        elif roll < 0.90:
            return random.randint(26, 30)
        return random.randint(31, 38)


class Bid(models.Model):
    """
    The 24h async claim mechanism -- used both for free-agent claims and for
    re-claiming a player whose contract just expired. Nobody needs to be
    online at the same time: a manager opens a window by placing the first
    bid, anyone can outbid until expires_at, then resolve_expired_bids
    (a scheduled job) settles it.
    """

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="bids")
    manager = models.ForeignKey(ManagerProfile, on_delete=models.CASCADE, related_name="bids")
    wage_offer = models.PositiveIntegerField()
    contract_length_years = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            # First bid on this player sets the 24h window; later bids on the
            # same open window should reuse the same expiry (enforced in the view).
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.manager} -> {self.player} ({self.wage_offer} KC/mo, {self.status})"


class Contract(models.Model):
    """A player's current/past employment under a manager."""

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="contracts")
    manager = models.ForeignKey(ManagerProfile, on_delete=models.CASCADE, related_name="contracts")
    wage = models.PositiveIntegerField()
    length_years = models.PositiveSmallIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.player} under {self.manager} ({self.wage} KC/mo)"


class ClubDeal(models.Model):
    """
    The negotiated agreement loaning a manager's player to a club. Both
    sides must agree (negotiation itself happens off-platform via Discord
    for the MVP; this record is the agreed outcome).
    """

    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="club_deals")
    manager = models.ForeignKey(ManagerProfile, on_delete=models.CASCADE, related_name="club_deals")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="club_deals")
    monthly_fee = models.PositiveIntegerField()
    signing_bonus = models.PositiveIntegerField(default=0)
    length_years = models.PositiveSmallIntegerField()
    start_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.player} on loan to {self.club} via {self.manager}"
