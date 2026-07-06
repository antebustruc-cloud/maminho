"""
Runs on the 1st of each month after wages. Updates every contracted player's
stats based on:
  - Talent type  (rate of natural improvement/decline)
  - Facility level  (soccer field bonus for football players)
  - Age  (players decline faster after peak, per talent_type)

Stats never go below 1 or above 30.
"""

import random

from django.core.management.base import BaseCommand
from django.db import transaction

from players.models import Player

FOOTBALL_STAT_FIELDS = [
    "agility", "strength", "speed", "acceleration", "jump", "stamina",
    "injury_resistance", "flexibility",
    "finishing", "passing", "dribbling", "first_touch", "crossing",
    "tackling", "marking", "positioning", "off_the_ball", "vision",
]

# Talent multipliers: how quickly a player improves in their prime.
# Positive = growth bias, negative = decline bias.
TALENT_GROWTH = {
    Player.TalentType.EARLY_PEAK: lambda age: 0.6 if age < 21 else (-0.3 if age > 23 else 0.0),
    Player.TalentType.TALENTED:   lambda age: 0.8 if age < 28 else -0.2,
    Player.TalentType.NORMAL:     lambda age: 0.3 if age < 26 else (-0.2 if age > 30 else 0.0),
    Player.TalentType.LATE_PEAK:  lambda age: 0.1 if age < 27 else (0.7 if age < 33 else -0.3),
}


def _stat_delta(talent_type, age, facility_bonus_pct):
    """
    Returns an integer delta to apply to each stat this month.
    Facility bonus scales the growth opportunity.
    """
    base_growth = TALENT_GROWTH[talent_type](age)
    # Facility bonus applies on top of natural growth (can't reverse a decline)
    facility_multiplier = 1 + facility_bonus_pct / 100
    adjusted = base_growth * facility_multiplier

    # Add noise: ±1 with low probability, weighted by adjusted growth
    roll = random.random()
    if adjusted >= 0.5 and roll < 0.4:
        return 1
    elif adjusted >= 0.2 and roll < 0.2:
        return 1
    elif adjusted <= -0.3 and roll < 0.3:
        return -1
    elif adjusted <= -0.1 and roll < 0.1:
        return -1
    return 0


class Command(BaseCommand):
    help = "Applies monthly stat changes to all contracted players."

    @transaction.atomic
    def handle(self, *args, **options):
        players = Player.objects.filter(
            is_free_agent=False
        ).select_related("current_club")

        updated = 0
        for player in players:
            facility_bonus = 0
            if player.current_club:
                facility = player.current_club.facilities.filter(facility_type="stadium").first()
                facility_bonus = facility.level if facility else 0

            delta = _stat_delta(player.talent_type, player.age, facility_bonus)
            if delta == 0:
                continue

            changed = False
            for field in FOOTBALL_STAT_FIELDS:
                current = getattr(player, field)
                new_val = max(1, min(30, current + delta))
                if new_val != current:
                    setattr(player, field, new_val)
                    changed = True

            if changed:
                player.save(update_fields=FOOTBALL_STAT_FIELDS)
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Updated stats for {updated} player(s)."))
