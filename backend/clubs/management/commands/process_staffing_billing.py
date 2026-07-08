"""
Monthly recurring staffing billing (Phase 3d): every active
FacilityStaffingContract charges the club owner — to the central bank for
in-house crews, to the provider company otherwise. Price-0 company
contracts are skipped (free deals are allowed).

A club that can't pay gets the contract cancelled (workers freed) and a
log line; nothing else breaks.

Joins the payroll cron day. Suggested cron (1st of month, 00:25):
  25 0 1 * * docker compose -f /root/maminho/docker-compose.yml \
      exec -T backend python manage.py process_staffing_billing >> /var/log/maminho/staffing.log 2>&1
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from clubs.models import FacilityStaffingContract
from clubs.services import _bill_staffing_contract
from economy.models import InsufficientFundsError, lc_display


class Command(BaseCommand):
    help = "Bills all active facility staffing contracts (monthly)."

    def handle(self, *args, **options):
        billed = cancelled = 0
        contracts = (FacilityStaffingContract.objects
                     .filter(active_until__isnull=True)
                     .select_related("facility__club", "provider_company"))
        for contract in contracts:
            try:
                with transaction.atomic():
                    _bill_staffing_contract(contract)
                billed += 1
            except InsufficientFundsError:
                contract.active_until = timezone.now()
                contract.save(update_fields=["active_until"])
                contract.assigned_employees.update(current_contract=None)
                cancelled += 1
                self.stdout.write(self.style.WARNING(
                    f"{contract.facility.club.name}: {contract.service_type} contract "
                    f"CANCELLED — can't pay {lc_display(contract.monthly_price_lc)}."
                ))

        self.stdout.write(self.style.SUCCESS(
            f"Staffing billing: {billed} contracts billed, {cancelled} cancelled."))
