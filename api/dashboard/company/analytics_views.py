from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from db.company import Company, CompanyJob, CompanyJobApplication
from db.task import Level, UserIgLink
from db.user import User, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType


def _get_company_for_request(request):
    try:
        user_id = JWTUtils.fetch_user_id(request)
    except Exception:
        return None, CustomResponse(
            general_message="User not found or token invalid",
            message={"error_code": "USER_NOT_FOUND"},
        ).get_failure_response(
            status_code=401,
            http_status_code=status.HTTP_401_UNAUTHORIZED,
        )

    user = User.objects.filter(id=user_id).first()
    if not user:
        return None, CustomResponse(
            general_message="User not found",
            message={"error_code": "USER_NOT_FOUND"},
        ).get_failure_response(
            status_code=401,
            http_status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if not UserRoleLink.objects.filter(user=user, role__title=RoleType.COMPANY.value).exists():
        return None, CustomResponse(
            general_message="Company role required",
            message={"error_code": "COMPANY_ROLE_REQUIRED"},
        ).get_failure_response(
            status_code=403,
            http_status_code=status.HTTP_403_FORBIDDEN,
        )

    company = Company.objects.filter(company_user_id=user, status="active").first()
    if not company:
        return None, CustomResponse(
            general_message="No active company profile found for this user",
            message={"error_code": "NO_ACTIVE_COMPANY"},
        ).get_failure_response(
            status_code=403,
            http_status_code=status.HTTP_403_FORBIDDEN,
        )
    return company, None


def _period_since(request):
    period = request.query_params.get("period", "30d")
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period)
    return timezone.now() - timedelta(days=days) if days else None


def _public_learners_qs(request):
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

    def get(self, request):
        company, error = _get_company_for_request(request)
        if error:
            return error

        since = _period_since(request)
        jobs = CompanyJob.objects.filter(company_id=company, is_deleted=False)
        apps = CompanyJobApplication.objects.filter(job__company_id=company)
        period_jobs = jobs.filter(created_at__gte=since) if since else jobs
        period_apps = apps.filter(created_at__gte=since) if since else apps

        quick_stats = {
            "jobs_posted": jobs.count(),
            "total_views": 0,
            "applications": apps.count(),
            "hired": apps.filter(status="accepted").count(),
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
                    {"key": "total_views", "label": "Total views", "value": quick_stats["total_views"], "delta": 0, "delta_type": "neutral", "period": request.query_params.get("period", "30d")},
                    {"key": "applications", "label": "Applications", "value": quick_stats["applications"], "delta": period_apps.count(), "delta_type": "increase", "period": request.query_params.get("period", "30d")},
                    {"key": "hired", "label": "Hired", "value": quick_stats["hired"], "delta": period_apps.filter(status="accepted").count(), "delta_type": "increase", "period": request.query_params.get("period", "30d")},
                ],
                "talent_pool": _talent_pool_payload(request),
            },
        ).get_success_response()


class CompanyTalentPoolAnalyticsAPIView(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request):
        _company, error = _get_company_for_request(request)
        if error:
            return error

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
