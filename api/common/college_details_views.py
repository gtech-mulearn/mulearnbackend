from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce

from db.organization import Organization, UserOrganizationLink
from db.user import User
from db.task import InterestGroup
from db.learning_circle import LearningCircle

from utils.response import CustomResponse
from utils.types import OrganizationType
from utils.utils import DateTimeUtils


class CollegeDetailsRateThrottle(AnonRateThrottle):
    rate = '60/minute'

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception:
            # Fallback to True if Redis cache is not available (e.g. locally)
            return True


class CollegeDetailsAPI(APIView):
    throttle_classes = [CollegeDetailsRateThrottle]

    def get(self, request, college_code):
        college_code = (college_code or "").strip()
        if not college_code:
            return CustomResponse(general_message="College not found").get_failure_response()

        org = (
            Organization.objects.select_related("district__zone", "college_org")
            .filter(code__iexact=college_code, org_type=OrganizationType.COLLEGE.value)
            .first()
        )
        if not org:
            return CustomResponse(general_message="College not found").get_failure_response()

        return CustomResponse(
            response={
                "campus_details": self._get_campus_details(org),
                "top_learners": self._get_top_learners(org),
                "ig_details": self._get_ig_details(org),
                "lc_details": self._get_lc_details(org),
            }
        ).get_success_response()

    def _get_campus_details(self, org):
        campus = org.college_org
        six_months_ago = DateTimeUtils.get_current_utc_time() - timedelta(weeks=26)
        members = org.user_organization_link_org

        return {
            "college_name": org.title,
            "campus_code": org.code,
            "campus_zone": (
                org.district.zone.name
                if getattr(org, "district", None) and org.district.zone
                else None
            ),
            "campus_level": campus.level if campus else None,
            "total_karma": (
                members.filter(user__wallet_user__isnull=False)
                .aggregate(total=Coalesce(Sum("user__wallet_user__karma"), 0))["total"]
            ),
            "total_members": members.count(),
            "active_members": members.filter(
                user__wallet_user__isnull=False,
                user__wallet_user__karma_last_updated_at__gte=six_months_ago,
            ).count(),
            "rank": self._get_campus_rank(org),
        }

    def _get_campus_rank(self, org):
        ranked_orgs = (
            UserOrganizationLink.objects.filter(
                org__org_type=OrganizationType.COLLEGE.value
            )
            .values("org")
            .annotate(total_karma=Coalesce(Sum("user__wallet_user__karma"), 0))
            .order_by("-total_karma", "org__created_at")
        )

        for position, row in enumerate(ranked_orgs, start=1):
            if row["org"] == org.id:
                return position

        # Unranked: brand-new campus with no member links yet
        return 0

    def _get_top_learners(self, org):
        top_learners_qs = (
            User.objects.filter(
                user_organization_link_user__org=org,
            )
            .exclude(user_organization_link_user__is_alumni=True)
            .distinct()
            .annotate(karma=Coalesce(F("wallet_user__karma"), 0))
            .order_by("-karma", "-created_at")
            .values("full_name", "muid", "karma", "profile_pic")[:20]
        )

        return [
            {
                "full_name": learner["full_name"],
                "muid": learner["muid"],
                "karma": learner["karma"],
                "profile_pic": (
                    str(learner["profile_pic"]) if learner["profile_pic"] else None
                ),
            }
            for learner in top_learners_qs
        ]

    def _get_ig_details(self, org):
        campus_member_filter = Q(
            user_ig_link_ig__user__user_organization_link_user__org=org,
            user_ig_link_ig__user__user_organization_link_user__verified=True,
        )

        ig_rows = (
            InterestGroup.objects.filter(
                status="active",
                user_ig_link_ig__user__user_organization_link_user__org=org,
                user_ig_link_ig__user__user_organization_link_user__verified=True,
            )
            .annotate(
                members=Count(
                    "user_ig_link_ig__user",
                    filter=campus_member_filter,
                    distinct=True,
                ),
                total_karma=Coalesce(
                    Sum(
                        "user_ig_link_ig__user__wallet_user__karma",
                        filter=campus_member_filter,
                    ),
                    0,
                ),
            )
            .values("name", "code", "members", "total_karma")
            .order_by("-members", "name")
        )

        return [
            {
                "ig_name": row["name"],
                "ig_code": row["code"],
                "members": row["members"],
                "total_karma": row["total_karma"],
            }
            for row in ig_rows
        ]

    def _get_lc_details(self, org):
        learning_circles_qs = (
            LearningCircle.objects.filter(org=org)
            .select_related("ig")
            .annotate(
                members=Count(
                    "user_circle_link_circle",
                    filter=Q(user_circle_link_circle__accepted=True),
                )
            )
            .values("title", "ig__code", "ig__name", "members")
            .order_by("-members", "title")
        )

        return [
            {
                "title": lc["title"] or "",
                "ig_code": lc["ig__code"] or "",
                "ig_name": lc["ig__name"] or "",
                "members": lc["members"],
            }
            for lc in learning_circles_qs
        ]
