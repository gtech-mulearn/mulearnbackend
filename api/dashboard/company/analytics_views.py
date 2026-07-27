from rest_framework.views import APIView
from django.db.models import Avg, Count, Sum, F
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import OrganizationType
from db.job import CompanyJob, UserJobApplication
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter, OpenApiTypes
from rest_framework import serializers
from .company_views import _get_company_for_user

class CompanyGigAnalyticsAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Analytics'],
        description="Retrieve analytics data for company gigs (creator or approved company mentor).",
        responses={
            200: inline_serializer(
                name='CompanyGigAnalyticsResponse',
                fields={
                    'total_gigs_posted': serializers.IntegerField(),
                    'active_gigs': serializers.IntegerField(),
                    'closed_gigs': serializers.IntegerField(),
                    'average_hourly_rate': serializers.FloatField(),
                    'application_funnel': serializers.DictField(),
                    'conversion_rate': serializers.CharField(),
                }
            )
        }
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)

        if not company:
            return CustomResponse(general_message="Company profile not found or access denied.").get_failure_response(status_code=404)

        gigs = CompanyJob.objects.filter(company=company, job_type='Gig', is_deleted=False)
        
        total_gigs_posted = gigs.count()
        active_gigs = gigs.filter(status='Active').count()
        closed_gigs = gigs.filter(status='Closed').count()
        
        avg_hourly_rate = gigs.aggregate(Avg('hourly_rate'))['hourly_rate__avg'] or 0.0

        applications = UserJobApplication.objects.filter(job__in=gigs)
        total_applications = applications.count()
        
        funnel_data = applications.values('status').annotate(count=Count('status'))
        funnel_dict = {
            "Total": total_applications,
            "Pending": 0,
            "In-Review": 0,
            "Shortlisted": 0,
            "Interview": 0,
            "Selected": 0,
            "Rejected": 0
        }
        
        for item in funnel_data:
            funnel_dict[item['status']] = item['count']
            
        selected_count = funnel_dict["Selected"]
        conversion_rate = f"{(selected_count / total_applications * 100):.2f}%" if total_applications > 0 else "0.00%"
        
        response_data = {
            "total_gigs_posted": total_gigs_posted,
            "active_gigs": active_gigs,
            "closed_gigs": closed_gigs,
            "average_hourly_rate": float(f"{avg_hourly_rate:.2f}"),
            "application_funnel": funnel_dict,
            "conversion_rate": conversion_rate
        }
        
        return CustomResponse(response=response_data).get_success_response()


class CompanyTaskAnalyticsAPI(APIView):
    """
    PRD §6.2/6.3 — task performance analytics parity with jobs: views were
    never tracked for tasks (no equivalent of CompanyJob.total_views exists
    on TaskList, so it's omitted rather than faked), but submissions,
    approval-funnel breakdown, completions, karma distributed, and learner
    satisfaction (from CompanyFeedback) now mirror what CompanyGigAnalyticsAPI
    already gives jobs.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Analytics'],
        description="Retrieve analytics data for company-submitted tasks (creator or approved company mentor).",
    )
    def get(self, request):
        from db.task import TaskList, KarmaActivityLog
        from db.company import CompanyFeedback

        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company:
            return CustomResponse(general_message="Company profile not found or access denied.").get_failure_response(status_code=404)

        tasks = TaskList.objects.filter(submitted_by_company=company, is_deleted=False)
        total_submitted = tasks.count()

        funnel_data = tasks.values("approval_status").annotate(count=Count("approval_status"))
        funnel_dict = {"Total": total_submitted, "approved": 0, "pending": 0, "rejected": 0, "changes_requested": 0}
        for item in funnel_data:
            funnel_dict[item["approval_status"]] = item["count"]

        task_ids = tasks.values_list("id", flat=True)
        completions = KarmaActivityLog.objects.filter(task_id__in=task_ids)
        total_completions = completions.count()
        karma_distributed = completions.aggregate(total=Sum("karma"))["total"] or 0

        feedback_agg = CompanyFeedback.objects.filter(
            company=company, interaction_type=CompanyFeedback.InteractionType.TASK,
        ).aggregate(avg=Avg("rating"), count=Count("id"))

        approved_count = funnel_dict["approved"]
        completion_rate = f"{(total_completions / approved_count * 100):.2f}%" if approved_count > 0 else "0.00%"

        return CustomResponse(response={
            "total_tasks_submitted": total_submitted,
            "approval_funnel": funnel_dict,
            "total_completions": total_completions,
            "completion_rate": completion_rate,
            "karma_distributed": karma_distributed,
            "learner_satisfaction": {
                "average_rating": round(feedback_agg["avg"], 2) if feedback_agg["avg"] else None,
                "rating_count": feedback_agg["count"] or 0,
            },
        }).get_success_response()


def _period_since(request):
    from django.utils import timezone
    from datetime import timedelta
    period = request.query_params.get("period", "30d")
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period)
    return timezone.now() - timedelta(days=days) if days else None


def _public_learners_qs(request):
    from db.user import User
    from utils.types import RoleType
    qs = User.objects.filter(
        suspended_at__isnull=True,
        user_settings_user__is_public=True,
    ).exclude(user_role_link_user__role__title=RoleType.COMPANY.value)

    if karma_min := request.query_params.get("karma_min"):
        qs = qs.filter(wallet_user__karma__gte=int(karma_min))
    if karma_max := request.query_params.get("karma_max"):
        qs = qs.filter(wallet_user__karma__lte=int(karma_max))
    if level_order_min := request.query_params.get("level_order_min"):
        qs = qs.filter(user_lvl_link_user__level__level_order__gte=int(level_order_min))
    if request.query_params.get("interested_in_work", "").lower() in ("true", "1", "yes"):
        qs = qs.filter(interested_in_work=True)
    if request.query_params.get("interested_in_gig_work", "").lower() in ("true", "1", "yes"):
        qs = qs.filter(interested_in_gig_work=True)
    if ig_ids := request.query_params.get("ig_ids"):
        qs = qs.filter(user_ig_link_user__ig_id__in=[i.strip() for i in ig_ids.split(",") if i.strip()])
    if district_id := request.query_params.get("district_id"):
        qs = qs.filter(user_organization_link_user__org__district_id=district_id)

    return qs.distinct()


def _talent_pool_payload(request):
    from db.user import User
    from db.task import Level, UserIgLink
    from django.db.models import Count, Sum
    from utils.types import RoleType

    learners = _public_learners_qs(request)
    total = learners.count()
    level_distribution = []
    for level in Level.objects.order_by("level_order"):
        count = learners.filter(user_lvl_link_user__level=level).count()
        level_distribution.append({
            "level_id": str(level.id),
            "level_name": level.name,
            "level_order": level.level_order,
            "count": count,
            "percentage": round((count / total) * 100, 2) if total else 0,
        })

    top_igs = (
        UserIgLink.objects.filter(user__in=learners, is_active=True)
        .values("ig_id", "ig__name")
        .annotate(
            learner_count=Count("user_id", distinct=True),
            total_karma=Sum("user__wallet_user__karma"),
        )
        .order_by("-learner_count")[:5]
    )

    return {
        "total_learners": total,
        "level_distribution": level_distribution,
        "top_interest_groups": [
            {
                "ig_id": item["ig_id"],
                "name": item["ig__name"],
                "learner_count": item["learner_count"],
                "total_karma": item["total_karma"] or 0,
            }
            for item in top_igs
        ],
    }


class CompanyDashboardSummaryAPIView(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Analytics'],
        description="Retrieve dashboard summary statistics for the active company.",
    )
    def get(self, request):
        from django.db.models import Sum
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company:
            return CustomResponse(
                general_message="Company profile not found or access denied."
            ).get_failure_response(status_code=404)

        since = _period_since(request)
        jobs = CompanyJob.objects.filter(company=company, is_deleted=False)
        apps = UserJobApplication.objects.filter(job__company=company)
        period_jobs = jobs.filter(created_at__gte=since) if since else jobs
        period_apps = apps.filter(applied_at__gte=since) if since else apps

        total_views = jobs.aggregate(total=Sum('total_views'))['total'] or 0

        quick_stats = {
            "jobs_posted": jobs.count(),
            "total_views": total_views,
            "applications": apps.count(),
            "hired": apps.filter(status="Selected").count(),
        }

        return CustomResponse(
            general_message="Company dashboard summary fetched successfully",
            response={
                "company": {
                    "id": str(company.id),
                    "name": company.name,
                    "slug": company.slug,
                    "status": company.status,
                    "logo": company.logo,
                },
                "quick_stats": quick_stats,
                "stat_cards": [
                    {"key": "jobs_posted", "label": "Jobs posted", "value": quick_stats["jobs_posted"], "delta": period_jobs.count(), "delta_type": "increase", "period": request.query_params.get("period", "30d")},
                    {"key": "total_views", "label": "Total views", "value": quick_stats["total_views"], "delta": total_views, "delta_type": "increase" if total_views > 0 else "neutral", "period": request.query_params.get("period", "30d")},
                    {"key": "applications", "label": "Applications", "value": quick_stats["applications"], "delta": period_apps.count(), "delta_type": "increase", "period": request.query_params.get("period", "30d")},
                    {"key": "hired", "label": "Hired", "value": quick_stats["hired"], "delta": period_apps.filter(status="Selected").count(), "delta_type": "increase", "period": request.query_params.get("period", "30d")},
                ],
                "talent_pool": _talent_pool_payload(request),
            },
        ).get_success_response()


class CompanyTalentPoolAnalyticsAPIView(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Analytics'],
        description="Retrieve analytics data for the talent pool.",
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company:
            return CustomResponse(
                general_message="Company profile not found or access denied."
            ).get_failure_response(status_code=404)

        try:
            response = _talent_pool_payload(request)
        except ValueError:
            return CustomResponse(
                general_message="Invalid numeric filter value",
                message={"error_code": "INVALID_FILTER_VALUE"},
            ).get_failure_response()

        return CustomResponse(
            general_message="Talent pool analytics fetched successfully",
            response=response,
        ).get_success_response()


class CompanyCampusAnalyticsAPIView(APIView):
    """
    PRD §12 — layers a campus dimension onto the existing job/task/event
    surfaces rather than building new analytics from scratch. Job and task
    breakdowns join directly through the user FK; event attendance is
    resolved in two steps since EventConnection.entity_id is a polymorphic
    plain CharField (no direct ORM join path), matching the same pattern
    used in CompanyImpactReportAPI.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Analytics'],
        description="Campus-segmented breakdown of job applicants, task completers, and event attendees for the authenticated company (top 10 campuses per surface).",
    )
    def get(self, request):
        from db.task import TaskList, KarmaActivityLog
        from db.events import Event, EventConnection
        from db.organization import UserOrganizationLink

        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company:
            return CustomResponse(
                general_message="Company profile not found or access denied."
            ).get_failure_response(status_code=404)

        jobs = CompanyJob.objects.filter(company=company, is_deleted=False)
        job_applicants_by_campus = list(
            UserJobApplication.objects.filter(
                job__in=jobs,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .values(
                campus_id=F("user__user_organization_link_user__org_id"),
                campus_name=F("user__user_organization_link_user__org__title"),
            )
            .annotate(applicant_count=Count("user_id", distinct=True))
            .order_by("-applicant_count")[:10]
        )

        tasks = TaskList.objects.filter(submitted_by_company=company, is_deleted=False)
        task_completers_by_campus = list(
            KarmaActivityLog.objects.filter(
                task__in=tasks,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .values(
                campus_id=F("user__user_organization_link_user__org_id"),
                campus_name=F("user__user_organization_link_user__org__title"),
            )
            .annotate(completer_count=Count("user_id", distinct=True))
            .order_by("-completer_count")[:10]
        )

        event_attendees_by_campus = []
        if company.org_id:
            events = Event.objects.filter(
                organiser_type=Event.OrganiserType.COMPANY, organiser_org_id=company.org_id,
            )
            attendee_ids = list(EventConnection.objects.filter(
                event__in=events, entity_type=EventConnection.EntityType.USER_TICKET,
                ticket_status=EventConnection.TicketStatus.ACTIVE,
            ).values_list("entity_id", flat=True))
            if attendee_ids:
                event_attendees_by_campus = list(
                    UserOrganizationLink.objects.filter(
                        user_id__in=attendee_ids, org__org_type=OrganizationType.COLLEGE.value,
                    )
                    .values(campus_id=F("org_id"), campus_name=F("org__title"))
                    .annotate(attendee_count=Count("user_id", distinct=True))
                    .order_by("-attendee_count")[:10]
                )

        return CustomResponse(response={
            "job_applicants_by_campus": job_applicants_by_campus,
            "task_completers_by_campus": task_completers_by_campus,
            "event_attendees_by_campus": event_attendees_by_campus,
        }).get_success_response()


class CompanyTalentPoolInsightsAPIView(APIView):
    """
    PRD §11.3 — export/reporting of talent-pool insights (e.g. "top skills
    among available students in district X") for company workforce
    planning. Reuses the same filter set as the talent-pool analytics
    endpoint (_public_learners_qs); add `?format=csv` for a downloadable
    report instead of the default JSON summary.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Analytics'],
        description="Top-skills and top-colleges insights across the (optionally filtered) talent pool. Pass format=csv for a CSV download.",
        parameters=[
            OpenApiParameter("district_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("format", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False, description="json (default) or csv"),
        ],
    )
    def get(self, request):
        from db.achievement import UserSkillProgress
        from db.skill import Skill
        from db.organization import UserOrganizationLink

        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company:
            return CustomResponse(
                general_message="Company profile not found or access denied."
            ).get_failure_response(status_code=404)

        try:
            learners = _public_learners_qs(request)
        except ValueError:
            return CustomResponse(
                general_message="Invalid numeric filter value",
                message={"error_code": "INVALID_FILTER_VALUE"},
            ).get_failure_response()

        top_skills_raw = list(
            UserSkillProgress.objects.filter(user__in=learners)
            .values("skill_id")
            .annotate(learner_count=Count("user_id", distinct=True))
            .order_by("-learner_count")[:10]
        )
        skill_names = {
            s.id: s.name for s in Skill.objects.filter(id__in=[r["skill_id"] for r in top_skills_raw])
        }
        top_skills = [
            {
                "skill_id": r["skill_id"],
                "skill_name": skill_names.get(r["skill_id"], r["skill_id"]),
                "learner_count": r["learner_count"],
            }
            for r in top_skills_raw
        ]

        top_colleges = list(
            UserOrganizationLink.objects.filter(
                user__in=learners, org__org_type=OrganizationType.COLLEGE.value,
            )
            .values(college_id=F("org_id"), college_name=F("org__title"))
            .annotate(learner_count=Count("user_id", distinct=True))
            .order_by("-learner_count")[:10]
        )

        if request.query_params.get("format", "json").lower() == "csv":
            import csv
            from django.http import HttpResponse

            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="talent_pool_insights.csv"'
            writer = csv.writer(response)
            writer.writerow(["Total Learners", learners.count()])
            writer.writerow([])
            writer.writerow(["Top Skills", "Learner Count"])
            for row in top_skills:
                writer.writerow([row["skill_name"], row["learner_count"]])
            writer.writerow([])
            writer.writerow(["Top Colleges", "Learner Count"])
            for row in top_colleges:
                writer.writerow([row["college_name"], row["learner_count"]])
            return response

        return CustomResponse(response={
            "total_learners": learners.count(),
            "top_skills": top_skills,
            "top_colleges": top_colleges,
        }).get_success_response()

