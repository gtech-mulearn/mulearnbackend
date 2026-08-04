from django.core.management.base import BaseCommand
from django.db.models.functions import Now
from db.mentor import MentorshipSession, MentorshipSessionUserLink


class Command(BaseCommand):
    help = "Bulk-transitions SCHEDULED mentorship sessions past their ends_at to COMPLETED."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting mentorship session status transitions..."))

        due_sessions = list(
            MentorshipSession.objects.filter(
                status=MentorshipSession.Status.SCHEDULED,
                ends_at__lte=Now(),
                is_deleted=False,
            )
        )

        if not due_sessions:
            self.stdout.write(self.style.SUCCESS("No sessions due for completion."))
            return

        session_ids = [s.id for s in due_sessions]
        MentorshipSession.objects.filter(id__in=session_ids).update(
            status=MentorshipSession.Status.COMPLETED, updated_at=Now()
        )

        # Record the mentor's contributed minutes for the session (session
        # duration) on their MENTOR participant link, and mark them attended.
        for session in due_sessions:
            duration_minutes = int((session.ends_at - session.starts_at).total_seconds() // 60)
            MentorshipSessionUserLink.objects.filter(
                session_id=session.id,
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
            ).update(
                attendance_status=MentorshipSessionUserLink.AttendanceStatus.ATTENDED,
                contributed_minutes=duration_minutes,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Transitioned {len(due_sessions)} scheduled mentorship sessions to completed."
        ))
