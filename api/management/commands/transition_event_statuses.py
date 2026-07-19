from django.core.management.base import BaseCommand
from django.db.models.functions import Now
from db.events import Event


class Command(BaseCommand):
    help = "Bulk transitions event statuses based on their start and end datetimes."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting event status transitions..."))

        # Transition published -> ongoing (event has started)
        ongoing_updated = Event.objects.filter(
            status=Event.Status.PUBLISHED,
            start_datetime__lte=Now(),
            deleted_at__isnull=True,
        ).update(status=Event.Status.ONGOING, updated_at=Now())
        
        if ongoing_updated > 0:
            self.stdout.write(self.style.SUCCESS(f"Transitioned {ongoing_updated} published events to ongoing."))

        # Transition ongoing -> completed (event has ended)
        completed_updated = Event.objects.filter(
            status=Event.Status.ONGOING,
            end_datetime__lte=Now(),
            deleted_at__isnull=True,
        ).update(status=Event.Status.COMPLETED, updated_at=Now())

        if completed_updated > 0:
            self.stdout.write(self.style.SUCCESS(f"Transitioned {completed_updated} ongoing events to completed."))

        self.stdout.write(self.style.SUCCESS("Event status transitions completed."))
