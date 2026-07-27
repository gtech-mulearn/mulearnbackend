from rest_framework.views import APIView
from django.db.models import Avg, Count
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils, DateTimeUtils
from db.company import Company, CompanyFeedback
from .company_views import _get_company_for_user
from . import feedback_serializers


def _resolve_feedback_target(interaction_type, entity_id, user_id):
    """
    Resolve (company, error_message) for a feedback submission. Verifies the
    submitting user actually participated in the named interaction before
    accepting feedback — this is the anti-spam gate PRD §13.3's structured
    capture implies (feedback tied to a real interaction, not a free-standing
    review).
    """
    from db.job import CompanyJob, UserJobApplication
    from db.task import TaskList, KarmaActivityLog
    from db.events import Event, EventConnection
    from db.mentor import MentorshipSession, MentorshipSessionUserLink

    if interaction_type == CompanyFeedback.InteractionType.JOB:
        job = CompanyJob.objects.filter(id=entity_id, is_deleted=False).first()
        if not job:
            return None, "Job not found."
        applied = UserJobApplication.objects.filter(
            user_id=user_id, job=job, status__in=["Selected", "Rejected"]
        ).exists()
        if not applied:
            return None, "You can only give feedback after your application has reached a final outcome."
        return job.company, None

    if interaction_type == CompanyFeedback.InteractionType.TASK:
        task = TaskList.objects.filter(id=entity_id, is_deleted=False).first()
        if not task or not task.submitted_by_company_id:
            return None, "Company task not found."
        completed = KarmaActivityLog.objects.filter(user_id=user_id, task=task).exists()
        if not completed:
            return None, "You can only give feedback on a task you've completed."
        return task.submitted_by_company, None

    if interaction_type == CompanyFeedback.InteractionType.EVENT:
        event = Event.objects.filter(id=entity_id, organiser_type=Event.OrganiserType.COMPANY).first()
        if not event or not event.organiser_org_id:
            return None, "Company event not found."
        attended = EventConnection.objects.filter(
            event=event, entity_type=EventConnection.EntityType.USER_TICKET,
            entity_id=user_id, ticket_status=EventConnection.TicketStatus.ACTIVE,
        ).exists()
        if not attended:
            return None, "You can only give feedback on an event you attended."
        company = Company.objects.filter(org_id=event.organiser_org_id, status="verified").first()
        if not company:
            return None, "Company not found."
        return company, None

    if interaction_type == CompanyFeedback.InteractionType.SESSION:
        session = MentorshipSession.objects.filter(
            id=entity_id, session_type=MentorshipSession.SessionType.COMPANY_SESSION,
            status=MentorshipSession.Status.COMPLETED,
        ).first()
        if not session or not session.entity_id:
            return None, "Completed company mentorship session not found."
        attended = MentorshipSessionUserLink.objects.filter(
            session=session, user_id=user_id, participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
        ).exists()
        if not attended:
            return None, "You can only give feedback on a session you attended as a mentee."
        company = Company.objects.filter(org_id=session.entity_id, status="verified").first()
        if not company:
            return None, "Company not found."
        return company, None

    return None, "Invalid interaction_type."


class CompanyFeedbackAPI(APIView):
    """PRD §13.3 — structured feedback capture at each interaction-completion point."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Analytics'],
        description=(
            "Submit structured feedback (1-5 rating + optional comment) for a completed "
            "interaction with a company: job application outcome, task completion, "
            "event attendance, or mentorship session."
        ),
        request=feedback_serializers.CompanyFeedbackCreateSerializer,
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        interaction_type = request.data.get("interaction_type")
        entity_id = request.data.get("entity_id")
        rating = request.data.get("rating")

        if interaction_type not in CompanyFeedback.InteractionType.values:
            return CustomResponse(general_message="Invalid interaction_type.").get_failure_response()
        if not entity_id:
            return CustomResponse(general_message="entity_id is required.").get_failure_response()
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return CustomResponse(general_message="rating must be an integer between 1 and 5.").get_failure_response()
        if rating < 1 or rating > 5:
            return CustomResponse(general_message="rating must be between 1 and 5.").get_failure_response()

        company, error = _resolve_feedback_target(interaction_type, entity_id, user_id)
        if error:
            return CustomResponse(general_message=error).get_failure_response(status_code=404 if not company else 400)

        if CompanyFeedback.objects.filter(
            company=company, interaction_type=interaction_type, entity_id=entity_id, submitted_by_id=user_id,
        ).exists():
            return CustomResponse(general_message="You have already submitted feedback for this interaction.").get_failure_response()

        CompanyFeedback.objects.create(
            company=company,
            interaction_type=interaction_type,
            entity_id=entity_id,
            submitted_by_id=user_id,
            rating=rating,
            comment=request.data.get("comment"),
        )
        return CustomResponse(general_message="Feedback submitted successfully.").get_success_response()


class CompanyFeedbackListAPI(APIView):
    """Company-facing view of feedback received (creator or approved company mentor)."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Analytics'],
        description="List feedback received by the authenticated company.",
        parameters=[
            OpenApiParameter("interaction_type", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: feedback_serializers.CompanyFeedbackSerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company:
            return CustomResponse(general_message="Company profile not found or access denied.").get_failure_response(status_code=404)

        feedback = CompanyFeedback.objects.filter(company=company).select_related("submitted_by").order_by("-created_at")
        interaction_type = request.query_params.get("interaction_type")
        if interaction_type:
            feedback = feedback.filter(interaction_type=interaction_type)

        paginated = CommonUtils.get_paginated_queryset(
            feedback, request,
            search_fields=["comment"],
            sort_fields={"created_at": "created_at", "rating": "rating"},
        )
        serializer = feedback_serializers.CompanyFeedbackSerializer(paginated.get("queryset"), many=True)
        return CustomResponse(
            response={"data": serializer.data, "pagination": paginated.get("pagination")}
        ).get_success_response()


def build_impact_summary(company):
    """
    PRD §13.3 — shared aggregation used by both the authenticated
    Impact Report endpoint and the public-profile opt-in summary, so the
    two never drift out of sync.
    """
    from db.job import CompanyJob, UserJobApplication
    from db.task import TaskList, KarmaActivityLog
    from db.events import Event, EventConnection
    from db.mentor import MentorshipSession, MentorshipSessionUserLink
    from django.db.models import Sum

    # --- Reach: distinct learners touched across every surface ---
    job_ids = CompanyJob.objects.filter(company=company, is_deleted=False).values_list("id", flat=True)
    job_applicants = set(UserJobApplication.objects.filter(job_id__in=job_ids).values_list("user_id", flat=True))

    task_ids = TaskList.objects.filter(submitted_by_company=company, is_deleted=False).values_list("id", flat=True)
    task_completers = set(KarmaActivityLog.objects.filter(task_id__in=task_ids).values_list("user_id", flat=True))

    event_attendees = set()
    session_ids = []
    if company.org_id:
        event_ids = Event.objects.filter(
            organiser_type=Event.OrganiserType.COMPANY, organiser_org_id=company.org_id,
        ).values_list("id", flat=True)
        event_attendees = set(EventConnection.objects.filter(
            event_id__in=event_ids, entity_type=EventConnection.EntityType.USER_TICKET,
            ticket_status=EventConnection.TicketStatus.ACTIVE,
        ).values_list("entity_id", flat=True))

        session_ids = list(MentorshipSession.objects.filter(
            session_type=MentorshipSession.SessionType.COMPANY_SESSION,
            entity_id=company.org_id, status=MentorshipSession.Status.COMPLETED,
        ).values_list("id", flat=True))

    session_mentees = set(MentorshipSessionUserLink.objects.filter(
        session_id__in=session_ids, participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
    ).values_list("user_id", flat=True)) if session_ids else set()

    reach = len(job_applicants | task_completers | event_attendees | session_mentees)

    # --- Quality signal: structured feedback + mentor-session ratings ---
    feedback_agg = CompanyFeedback.objects.filter(company=company).aggregate(avg=Avg("rating"), count=Count("id"))

    session_rating_agg = {"avg": None, "count": 0}
    if session_ids:
        session_rating_agg = MentorshipSessionUserLink.objects.filter(
            session_id__in=session_ids,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
            rating__isnull=False,
        ).aggregate(avg=Avg("rating"), count=Count("id"))

    combined_count = (feedback_agg["count"] or 0) + (session_rating_agg["count"] or 0)
    combined_avg = None
    if combined_count:
        weighted = (feedback_agg["avg"] or 0) * (feedback_agg["count"] or 0) + \
                   (session_rating_agg["avg"] or 0) * (session_rating_agg["count"] or 0)
        combined_avg = round(weighted / combined_count, 2)

    # --- Outcome signal: hires + karma distributed ---
    hires = UserJobApplication.objects.filter(job_id__in=job_ids, status="Selected").count()
    karma_total = KarmaActivityLog.objects.filter(task_id__in=task_ids).aggregate(total=Sum("karma"))["total"] or 0

    return {
        "company": {"id": str(company.id), "name": company.name},
        "reach": {
            "total_learners_touched": reach,
            "job_applicants": len(job_applicants),
            "task_completers": len(task_completers),
            "event_attendees": len(event_attendees),
            "session_mentees": len(session_mentees),
        },
        "quality_signal": {
            "average_rating": combined_avg,
            "total_ratings": combined_count,
            "feedback_average_rating": round(feedback_agg["avg"], 2) if feedback_agg["avg"] else None,
            "feedback_count": feedback_agg["count"] or 0,
            "session_average_rating": round(session_rating_agg["avg"], 2) if session_rating_agg["avg"] else None,
            "session_rating_count": session_rating_agg["count"] or 0,
        },
        "outcome_signal": {
            "hires": hires,
            "karma_distributed": karma_total,
        },
    }


class CompanyImpactReportAPI(APIView):
    """
    PRD §13.3 — the company-facing Impact Report: aggregate reach, quality
    signal (structured feedback + mentor-session ratings), and outcome
    signal (hires, karma distributed).
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Analytics'],
        description="Aggregate impact report: reach, quality signal, and outcome signal for the authenticated company.",
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company:
            return CustomResponse(general_message="Company profile not found or access denied.").get_failure_response(status_code=404)

        return CustomResponse(response=build_impact_summary(company)).get_success_response()


class CompanyImpactReportPublishAPI(APIView):
    """Owner-only: toggle whether the Impact Report summary is shown on the public profile."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Analytics'],
        description="Opt in/out of publishing a summarized Impact Report on your public profile (owner or accepted co-admin only).",
    )
    def patch(self, request):
        from api.dashboard.company.company_views import is_company_owner_or_admin

        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company or not is_company_owner_or_admin(user_id, company):
            return CustomResponse(general_message="You must be the company owner or an accepted co-admin.").get_failure_response(status_code=403)

        publish = bool(request.data.get("publish", True))
        company.publish_impact_report = publish
        company.updated_by = user_id
        company.save(update_fields=["publish_impact_report", "updated_by", "updated_at"])
        return CustomResponse(
            general_message=f"Impact report {'published' if publish else 'unpublished'} on your public profile."
        ).get_success_response()
