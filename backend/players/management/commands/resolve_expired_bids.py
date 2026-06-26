from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from players.models import Bid, Contract, Player


class Command(BaseCommand):
    """
    Settles every 24h bidding window that has closed. Intended to run on a
    schedule (cron every few minutes) -- see backend/README.md for the
    crontab line. Idempotent: only touches bids that are still OPEN and past
    their expires_at, so running it twice in a row is harmless.
    """

    help = "Resolves expired free-agent bidding windows, awarding contracts to the highest bidder."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        expired_player_ids = (
            Bid.objects.filter(status=Bid.Status.OPEN, expires_at__lte=now)
            .values_list("player_id", flat=True)
            .distinct()
        )

        resolved_count = 0
        for player_id in expired_player_ids:
            bids = list(
                Bid.objects.select_for_update()
                .filter(player_id=player_id, status=Bid.Status.OPEN, expires_at__lte=now)
                .order_by("-wage_offer", "created_at")
            )
            if not bids:
                continue

            winning_bid, losing_bids = bids[0], bids[1:]
            player = Player.objects.select_for_update().get(id=player_id)

            Contract.objects.create(
                player=player,
                manager=winning_bid.manager,
                wage=winning_bid.wage_offer,
                length_years=winning_bid.contract_length_years,
                start_date=date.today(),
                end_date=date.today().replace(
                    year=date.today().year + winning_bid.contract_length_years
                ),
            )
            player.is_free_agent = False
            player.current_manager = winning_bid.manager
            player.save(update_fields=["is_free_agent", "current_manager"])

            winning_bid.status = Bid.Status.WON
            winning_bid.save(update_fields=["status"])
            Bid.objects.filter(id__in=[b.id for b in losing_bids]).update(status=Bid.Status.LOST)

            resolved_count += 1

        self.stdout.write(self.style.SUCCESS(f"Resolved {resolved_count} expired bidding window(s)."))
