"""
Monthly NPC payroll (Phase 3c): each active company pays the sum of its
active employees' wages from the company balance INTO the central bank
(the ledger's Admin infinite pool — the existing null-party account
concept, so no new account row is needed). Transaction kind: npc_wage.

A company that can't cover payroll is SUSPENDED (is_active=False) and
logged — workers are NOT auto-fired and the company is NOT dissolved;
the admin handles suspended companies manually for now.

Runs the day after player wages. Suggested cron (1st of month, 00:20):
  20 0 1 * * docker compose -f /root/maminho/docker-compose.yml \
      exec -T backend python manage.py process_npc_wages >> /var/log/maminho/npc_wages.log 2>&1
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from companies.models import Company
from economy.models import InsufficientFundsError, Transaction, lc_display, move_kc


class Command(BaseCommand):
    help = "Processes monthly NPC workforce wages for all active companies."

    def handle(self, *args, **options):
        paid = suspended = 0
        for company in Company.objects.filter(is_active=True):
            total = (company.employees.filter(fired_at__isnull=True)
                     .aggregate(total=Sum("monthly_wage_lc"))["total"]) or 0
            if total == 0:
                continue
            try:
                with transaction.atomic():
                    move_kc(from_holder=company, to_holder=None, amount=total,
                            kind=Transaction.Kind.NPC_WAGE,
                            description=f"Monthly NPC payroll for {company.name}")
                paid += 1
                self.stdout.write(f"{company.name}: paid {lc_display(total)} payroll.")
            except InsufficientFundsError:
                company.is_active = False
                company.save(update_fields=["is_active"])
                suspended += 1
                self.stdout.write(self.style.WARNING(
                    f"{company.name}: SUSPENDED — cannot cover {lc_display(total)} payroll "
                    f"(balance {lc_display(company.kc_balance)}). Admin action required."
                ))

        self.stdout.write(self.style.SUCCESS(
            f"NPC payroll: {paid} companies paid, {suspended} suspended."))
