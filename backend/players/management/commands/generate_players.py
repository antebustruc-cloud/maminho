import random

from django.core.management.base import BaseCommand
from django.db import transaction

from clubs.models import SportLicense
from players.models import Player
from players.namegen import DEFAULT_COUNTRY, generate_name, supported_countries

COUNTRY_DISPLAY = {"HR": "Croatia"}


class Command(BaseCommand):
    help = "Seeds the free-agent pool with generated players for any sport."

    def add_arguments(self, parser):
        parser.add_argument(
            "count", type=int, nargs="?", default=200,
            help="How many players to generate (default: 200).",
        )
        parser.add_argument(
            "--sport", default=SportLicense.Sport.FOOTBALL,
            choices=sorted(SportLicense.ACTIVE_SPORTS),
            help="Sport to generate players for (default: football). Only "
                 "launch-set (active) sports can have players generated.",
        )
        parser.add_argument(
            "--nationality", default=DEFAULT_COUNTRY,
            choices=supported_countries(),
            help="ISO country code driving name generation (default: HR).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        sport = options["sport"]
        nationality = options["nationality"]
        stat_field_names = [
            "agility", "strength", "speed", "acceleration", "jump", "stamina",
            "injury_resistance", "flexibility", "aggression", "bravery",
            "composure", "work_rate", "team_spirit", "influence", "finishing",
            "passing", "dribbling", "first_touch", "crossing", "tackling",
            "marking", "positioning", "off_the_ball", "vision",
        ]
        talent_weights = [
            (Player.TalentType.NORMAL, 0.55),
            (Player.TalentType.TALENTED, 0.20),
            (Player.TalentType.EARLY_PEAK, 0.15),
            (Player.TalentType.LATE_PEAK, 0.10),
        ]

        players = []
        for _ in range(count):
            kwargs = {name: Player.random_stat() for name in stat_field_names}
            talent_type = random.choices(
                [t for t, _ in talent_weights],
                weights=[w for _, w in talent_weights],
            )[0]
            players.append(Player(
                name=generate_name(nationality),
                sport=sport,
                age=Player.random_age(),
                height_cm=random.randint(170, 200),
                weight_kg=random.randint(65, 95),
                country=COUNTRY_DISPLAY.get(nationality, nationality),
                nationality=nationality,
                talent_type=talent_type,
                is_free_agent=True,
                **kwargs,
            ))

        Player.objects.bulk_create(players)
        self.stdout.write(self.style.SUCCESS(f"Generated {count} free-agent {sport} players."))
