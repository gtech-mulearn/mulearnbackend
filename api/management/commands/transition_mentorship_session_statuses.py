from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.functions import Now
from django.utils import timezone

from db.mentor import MentorshipSession, MentorshipSessionUserLink


class Command(BaseCommand):
    help = "Transitions SCHEDULED mentorship sessions past their ends_at to COMPLETED."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting mentorship session status transitions..."))

        candidate_ids = list(
            MentorshipSession.objects.filter(
                status=MentorshipSession.Status.SCHEDULED,
                ends_at__lte=Now(),
                is_deleted=False,
            ).values_list("id", flat=True)
        )

        if not candidate_ids:
            self.stdout.write(self.style.SUCCESS("No sessions due for completion."))
            return

        completed = 0
        for session_id in candidate_ids:
            # One short transaction per session: lock the row and re-check it,
            # because between the list query above and now an admin may have
            # cancelled the session or the mentor may have moved it into the
            # future. The status change and the mentor's minutes are written
            # together, so they can never disagree.
            with transaction.atomic():
                session = (
                    MentorshipSession.objects.select_for_update()
                    .filter(
                        id=session_id,
                        status=MentorshipSession.Status.SCHEDULED,
                        ends_at__lte=timezone.now(),
                        is_deleted=False,
                    )
                    .first()
                )
                if session is None:
                    continue

                session.status = MentorshipSession.Status.COMPLETED
                session.save(update_fields=["status", "updated_at"])

                # Record the mentor's contributed minutes (session duration) on
                # their MENTOR participant link, and mark them attended. The DB
                # only accepts minutes > 0 (chk_contrib_minutes).
                duration_minutes = int((session.ends_at - session.starts_at).total_seconds() // 60)
                MentorshipSessionUserLink.objects.filter(
                    session_id=session.id,
                    participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
                ).update(
                    attendance_status=MentorshipSessionUserLink.AttendanceStatus.ATTENDED,
                    contributed_minutes=duration_minutes if duration_minutes > 0 else None,
                )
                completed += 1

        self.stdout.write(self.style.SUCCESS(
            f"Transitioned {completed} scheduled mentorship sessions to completed."
        ))
