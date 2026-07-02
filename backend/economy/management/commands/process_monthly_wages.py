"""
Runs on the 1st of each month (cron). Processes two payment flows:

  1. Club → Manager: monthly_fee from every active ClubDeal
  2. Manager → Player wage: deducted from the manager's KC balance

If either party can't pay, the deal/contract is flagged rather than
silently skipped, so the admin can investigate via the Django admin.
Both transactions are logged to the economy_transaction table.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from economy.models import InsufficientFundsError, Transaction, move_kc
from players.models import ClubDeal, Contract


class Command(BaseCommand):
    help = "Processes monthly wage payments for all active club deals and player contracts."

    def handle(self, *args, **options):
        self._process_club_deals()
        self._process_player_wages()

    @transaction.atomic
    def _process_club_deals(self):
        """Club pays manager monthly_fee for each active ClubDeal."""
        deals = ClubDeal.objects.filter(is_active=True).select_related("club", "manager")
        paid = failed = 0
        for deal in deals:
            try:
                move_kc(
                    from_holder=deal.club,
                    to_holder=deal.manager,
                    amount=deal.monthly_fee,
                    kind=Transaction.Kind.CLUB_DEAL_FEE,
                    description=f"Monthly fee: {deal.player.name} @ {deal.club.name}",
                )
                paid += 1
            except InsufficientFundsError:
                self.stdout.write(
                    self.style.WARNING(
                        f"Club {deal.club.name} can't pay monthly fee for deal #{deal.id} "
                        f"(needs {deal.monthly_fee} KC, has {deal.club.kc_balance} KC)"
                    )
                )
                failed += 1
        self.stdout.write(self.style.SUCCESS(f"Club→Manager fees: {paid} paid, {failed} failed."))

    @transaction.atomic
    def _process_player_wages(self):
        """Manager pays player wage from each active Contract."""
        contracts = Contract.objects.filter(is_active=True).select_related("manager", "player")
        paid = failed = 0
        for contract in contracts:
            try:
                move_kc(
                    from_holder=contract.manager,
                    to_holder=None,   # wages leave the economy (paid to the player who isn't a user)
                    amount=contract.wage,
                    kind=Transaction.Kind.WAGE_PAYMENT,
                    description=f"Wage: {contract.player.name}",
                )
                paid += 1
            except InsufficientFundsError:
                self.stdout.write(
                    self.style.WARNING(
                        f"Manager {contract.manager} can't pay wage for {contract.player.name} "
                        f"(needs {contract.wage} KC, has {contract.manager.kc_balance} KC)"
                    )
                )
                failed += 1
        self.stdout.write(self.style.SUCCESS(f"Manager→Player wages: {paid} paid, {failed} failed."))
