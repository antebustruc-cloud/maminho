"""
Runs once per season at rollover (cron). Phase 3c: 1 real year = 3
seasons (~4 months each), so EVERY player in the game — all sports, team
and individual alike — gets age +1 per season (+3 per real year).

Idempotent per season period: the AgeProcessingLog unique constraint
guarantees that a double-run within the same period does nothing. To
deliberately re-run, delete the log row via the admin first.

Suggested cron (1st day of Jan/May/Sep at 00:15, after wages/stats):
  15 0 1 1,5,9 * docker compose -f /root/maminho/docker-compose.yml \
      exec -T backend python manage.py age_players >> /var/log/maminho/aging.log 2>&1
"""

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.db.models import F

from clubs.models import Season
from players.models import AgeProcessingLog, Player


class Command(BaseCommand):
    help = "Ages ALL players by +1 year (runs once per season; idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--period",
            help='Override the season period label (e.g. "S2 2026"). Defaults to the current period.',
        )

    def handle(self, *args, **options):
        period = options.get("period") or Season.current_period_name()

        if AgeProcessingLog.objects.filter(period=period).exists():
            self.stdout.write(self.style.WARNING(
                f"Players were already aged for {period} — skipping (idempotency guard)."
            ))
            return

        try:
            with transaction.atomic():
                # Claim the period first; the unique constraint rejects a
                # concurrent second run before any ages are touched.
                log = AgeProcessingLog.objects.create(period=period)
                aged = Player.objects.update(age=F("age") + 1)
                log.players_aged = aged
                log.save(update_fields=["players_aged"])
        except IntegrityError:
            self.stdout.write(self.style.WARNING(
                f"Another run already claimed {period} — skipping."
            ))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Aged {aged} players by +1 year for {period}."
        ))
