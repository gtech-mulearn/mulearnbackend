from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from db.mu_events import EventOutbox


class Command(BaseCommand):
    help = (
        "Re-queue already-dispatched μCoin events for redelivery (disaster "
        "recovery / mucoin-service backfill). Safe: mucoin-service dedupes by "
        "event id, so replays never double-pay."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            required=True,
            help="ISO timestamp; events created at/after this are re-queued (e.g. 2026-08-01T00:00:00)",
        )

    def handle(self, *args, **options):
        try:
            since = datetime.fromisoformat(options["since"])
        except ValueError as exc:
            raise CommandError(f"--since must be an ISO timestamp: {exc}") from exc
        count = EventOutbox.objects.filter(
            created_at__gte=since, dispatched_at__isnull=False
        ).update(dispatched_at=None, attempts=0, next_retry_at=None)
        self.stdout.write(self.style.SUCCESS(f"Re-queued {count} event(s) since {since}."))
