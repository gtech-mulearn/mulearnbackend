from rest_framework.views import APIView
from django.db.models import Avg, Count, Sum
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from db.job import CompanyJob, UserJobApplication
from drf_spectacular.utils import extend_schema, inline_serializer
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

