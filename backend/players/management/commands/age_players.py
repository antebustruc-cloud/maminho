"""
Runs once per real-world quarter at season rollover (cron). One real
quarter = one in-game year, so EVERY player in the game — all sports,
team and individual alike — gets age +1.

Idempotent per quarter: the AgeProcessingLog unique constraint guarantees
that a double-run within the same quarter does nothing. Use --force only
to deliberately re-run after deleting the log row via the admin.

Suggested cron (1st day of Jan/Apr/Jul/Oct at 00:15, after wages/stats):
  15 0 1 1,4,7,10 * docker compose -f /root/maminho/docker-compose.yml \
      exec -T backend python manage.py age_players >> /var/log/maminho/aging.log 2>&1
"""

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.db.models import F

from clubs.models import Season
from players.models import AgeProcessingLog, Player


class Command(BaseCommand):
    help = "Ages ALL players by +1 year (runs once per real quarter; idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--quarter",
            help='Override the quarter label (e.g. "Q3 2026"). Defaults to the current real quarter.',
        )

    def handle(self, *args, **options):
        quarter = options.get("quarter") or Season.current_quarter_name()

        if AgeProcessingLog.objects.filter(quarter=quarter).exists():
            self.stdout.write(self.style.WARNING(
                f"Players were already aged for {quarter} — skipping (idempotency guard)."
            ))
            return

        try:
            with transaction.atomic():
                # Claim the quarter first; the unique constraint rejects a
                # concurrent second run before any ages are touched.
                log = AgeProcessingLog.objects.create(quarter=quarter)
                aged = Player.objects.update(age=F("age") + 1)
                log.players_aged = aged
                log.save(update_fields=["players_aged"])
        except IntegrityError:
            self.stdout.write(self.style.WARNING(
                f"Another run already claimed {quarter} — skipping."
            ))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Aged {aged} players by +1 year for {quarter}."
        ))
