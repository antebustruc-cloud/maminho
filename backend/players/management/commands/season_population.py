"""
Season-rollover population maintenance (Phase 3d — SKELETON scope):

1. RETIREMENT: players older than RETIREMENT_AGE (34) are marked retired
   and released — freed from club, manager, and active contracts/deals.
2. YOUTH INTAKE: per active sport, 30-40 new players aged 16-18 with
   low-to-promising ratings join the free-agent pool.
3. TOP-UP: per active sport, the free-agent pool is topped up toward
   FREE_AGENT_POOL_TARGET if below (soft target, not a hard cap).

Idempotent per season period (SeasonPopulationLog guard, same pattern as
age_players). Runs alongside age_players at rollover.

Suggested cron (1st of Jan/May/Sep at 00:30, after age_players):
  30 0 1 1,5,9 * docker compose -f /root/maminho/docker-compose.yml \
      exec -T backend python manage.py season_population >> /var/log/maminho/population.log 2>&1
"""

import random

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.utils import timezone

from clubs.models import Season, SportLicense
from maminho import limits
from players.models import ClubDeal, Contract, Player, SeasonPopulationLog


class Command(BaseCommand):
    help = "Season rollover: retire old players, youth intake, free-agent top-up."

    def add_arguments(self, parser):
        parser.add_argument(
            "--period",
            help='Override the season period label (e.g. "S2 2026").',
        )

    def handle(self, *args, **options):
        period = options.get("period") or Season.current_period_name()

        if SeasonPopulationLog.objects.filter(period=period).exists():
            self.stdout.write(self.style.WARNING(
                f"Population already processed for {period} — skipping."))
            return

        try:
            with transaction.atomic():
                log = SeasonPopulationLog.objects.create(period=period)

                # 1. retirement
                retirees = Player.objects.filter(
                    age__gt=limits.RETIREMENT_AGE, is_retired=False)
                retired = 0
                for player in retirees:
                    Contract.objects.filter(player=player, is_active=True).update(is_active=False)
                    ClubDeal.objects.filter(player=player, is_active=True).update(is_active=False)
                    player.is_retired = True
                    player.is_free_agent = False
                    player.current_club = None
                    player.current_manager = None
                    player.save(update_fields=[
                        "is_retired", "is_free_agent", "current_club", "current_manager"])
                    retired += 1

                # 2. youth intake per active sport
                youth_total = 0
                for sport in sorted(SportLicense.ACTIVE_SPORTS):
                    intake = random.randint(limits.YOUTH_INTAKE_MIN, limits.YOUTH_INTAKE_MAX)
                    self._generate_youth(sport, intake)
                    youth_total += intake

                # 3. top up free-agent pool toward target
                topped_total = 0
                for sport in sorted(SportLicense.ACTIVE_SPORTS):
                    pool = Player.objects.filter(
                        sport=sport, is_free_agent=True, is_retired=False).count()
                    deficit = limits.FREE_AGENT_POOL_TARGET - pool
                    if deficit > 0:
                        call_command("generate_players", deficit, sport=sport)
                        topped_total += deficit

                log.retired = retired
                log.youth_generated = youth_total
                log.topped_up = topped_total
                log.save(update_fields=["retired", "youth_generated", "topped_up"])
        except IntegrityError:
            self.stdout.write(self.style.WARNING(
                f"Another run already claimed {period} — skipping."))
            return

        self.stdout.write(self.style.SUCCESS(
            f"{period}: retired {retired}, youth +{youth_total}, top-up +{topped_total}."))

    def _generate_youth(self, sport, count):
        """Youth prospects: age 16-18, low-to-promising ratings (capped rolls
        with a promising tail), straight into the free-agent pool."""
        stat_field_names = [
            "agility", "strength", "speed", "acceleration", "jump", "stamina",
            "injury_resistance", "flexibility", "aggression", "bravery",
            "composure", "work_rate", "team_spirit", "influence", "finishing",
            "passing", "dribbling", "first_touch", "crossing", "tackling",
            "marking", "positioning", "off_the_ball", "vision",
        ]
        from players.namegen import DEFAULT_COUNTRY, generate_name

        def youth_stat():
            # 80% land 1-8, 15% 9-14, 5% 15-20 — low to promising.
            roll = random.random()
            if roll < 0.80:
                return random.randint(1, 8)
            elif roll < 0.95:
                return random.randint(9, 14)
            return random.randint(15, 20)

        players = []
        for _ in range(count):
            kwargs = {name: youth_stat() for name in stat_field_names}
            talent = random.choices(
                [Player.TalentType.NORMAL, Player.TalentType.TALENTED,
                 Player.TalentType.EARLY_PEAK, Player.TalentType.LATE_PEAK],
                weights=[0.45, 0.30, 0.10, 0.15])[0]
            players.append(Player(
                name=generate_name(DEFAULT_COUNTRY),
                sport=sport,
                age=random.randint(limits.YOUTH_AGE_MIN, limits.YOUTH_AGE_MAX),
                height_cm=random.randint(168, 198),
                weight_kg=random.randint(60, 90),
                country="Croatia",
                nationality=DEFAULT_COUNTRY,
                talent_type=talent,
                is_free_agent=True,
                **kwargs,
            ))
        Player.objects.bulk_create(players)
