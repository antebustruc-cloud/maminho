"""
Flips construction projects whose ends_at has passed to COMPLETED and
applies the new facility level. Facilities activate immediately on
completion. Safe to run as often as you like (idempotent — only touches
active projects that have actually ended).

Suggested cron (every 10 minutes):
  */10 * * * * docker compose -f /root/maminho/docker-compose.yml \
      exec -T backend python manage.py complete_construction >> /var/log/maminho/construction.log 2>&1
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from clubs.models import ConstructionProject


class Command(BaseCommand):
    help = "Completes ended construction projects and applies new facility levels."

    def handle(self, *args, **options):
        now = timezone.now()
        due = ConstructionProject.objects.filter(
            status__in=(ConstructionProject.Status.PENDING,
                        ConstructionProject.Status.IN_PROGRESS),
            ends_at__lte=now,
        ).select_related("facility")

        completed = 0
        for project in due:
            with transaction.atomic():
                project.status = ConstructionProject.Status.COMPLETED
                project.save(update_fields=["status"])
                facility = project.facility
                facility.level = project.to_level
                facility.save(update_fields=["level"])
                # Free the assigned crews (Phase 3c).
                project.assigned_employees.update(current_project=None)
                completed += 1
                self.stdout.write(
                    f"Completed: {facility.club.name} {facility.facility_type} "
                    f"L{project.from_level}->L{project.to_level}"
                )

        self.stdout.write(self.style.SUCCESS(f"{completed} project(s) completed."))
