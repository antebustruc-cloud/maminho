import random

from django.core.management.base import BaseCommand
from django.db import transaction

from clubs.models import SportLicense
from players.models import Player

FIRST_NAMES = [
    "Luka", "Ivan", "Marko", "Ante", "Filip", "Josip", "Petar", "Domagoj",
    "Mateo", "Niko", "Karlo", "Borna", "Dario", "Tomislav", "Vedran",
]
LAST_NAMES = [
    "Horvat", "Kovacic", "Babic", "Maric", "Jurisic", "Novak", "Tomic",
    "Kralj", "Vukovic", "Matic", "Pavlic", "Simic", "Knezevic", "Barisic",
]
COUNTRIES = [
    "Croatia", "Germany", "Brazil", "Argentina", "Netherlands", "France",
    "Spain", "Italy", "Serbia", "Japan", "USA", "England",
]


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


class Command(BaseCommand):
    help = "Seeds the free-agent pool with generated players for any sport."

    def add_arguments(self, parser):
        parser.add_argument(
            "count", type=int, nargs="?", default=200,
            help="How many players to generate (default: 200).",
        )
        parser.add_argument(
            "--sport", default=SportLicense.Sport.FOOTBALL,
            choices=SportLicense.Sport.values,
            help="Sport to generate players for (default: football). "
                 "Attributes are generic for now; per-sport attribute models come later.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        sport = options["sport"]
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
                name=random_name(),
                sport=sport,
                age=Player.random_age(),
                height_cm=random.randint(170, 200),
                weight_kg=random.randint(65, 95),
                country=random.choice(COUNTRIES),
                talent_type=talent_type,
                is_free_agent=True,
                **kwargs,
            ))

        Player.objects.bulk_create(players)
        self.stdout.write(self.style.SUCCESS(f"Generated {count} free-agent {sport} players."))
