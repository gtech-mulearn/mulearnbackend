from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from django.db.models import Count, F, Q, Subquery, OuterRef, Sum

from db.organization import Organization, UserOrganizationLink
from db.user import User
from db.task import Wallet
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
        org = Organization.objects.filter(
            code=college_code, org_type=OrganizationType.COLLEGE.value
        ).first()
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
            "campus_zone": org.district.zone.name if org.district and org.district.zone else None,
            "campus_level": campus.level if campus else None,
            "total_karma": (
                members.filter(user__wallet_user__isnull=False)
                .aggregate(total=Sum("user__wallet_user__karma"))["total"]
                or 0
            ),
            "total_members": members.count(),
            "active_members": members.filter(
                user__wallet_user__isnull=False,
                user__wallet_user__karma_last_updated_at__gte=six_months_ago,
            ).count(),
            "rank": self._get_campus_rank(org),
        }

    def _get_campus_rank(self, org):
        org_karma = (
            UserOrganizationLink.objects.filter(
                org__org_type=OrganizationType.COLLEGE.value
            )
            .values("org")
            .annotate(total_karma=Sum("user__wallet_user__karma"))
            .order_by("-total_karma", "org__created_at")
        )

        rank_dict = {
            row["org"]: row["total_karma"] if row["total_karma"] is not None else 0
            for row in org_karma
        }
        sorted_orgs = sorted(rank_dict.items(), key=lambda item: item[1], reverse=True)

        for position, (org_id, _) in enumerate(sorted_orgs, start=1):
            if org_id == org.id:
                return position

    def _get_top_learners(self, org):
        top_learners_qs = (
            User.objects.filter(
                user_organization_link_user__org=org,
                user_organization_link_user__is_alumni=False,
            )
            .annotate(karma=F("wallet_user__karma"))
            .order_by("-karma", "-created_at")
            .values("full_name", "muid", "karma", "profile_pic")[:20]
        )

        return [
            {
                "full_name": learner["full_name"],
                "muid": learner["muid"],
                "karma": learner["karma"] or 0,
                "profile_pic": (
                    str(learner["profile_pic"]) if learner["profile_pic"] else None
                ),
            }
            for learner in top_learners_qs
        ]

    def _get_ig_details(self, org):
        wallet_karma_sq = Wallet.objects.filter(user=OuterRef("pk")).values("karma")[:1]

        rows = (
            User.objects.filter(
                user_organization_link_user__org=org,
                user_organization_link_user__verified=True,
                user_ig_link_user__ig__status="active",
            )
            .annotate(user_karma=Subquery(wallet_karma_sq))
            .values(
                "id",
                "user_ig_link_user__ig__name",
                "user_ig_link_user__ig__code",
                "user_karma",
            )
            .distinct()
        )

        ig_map = {}
        for row in rows:
            ig_code = row["user_ig_link_user__ig__code"]
            if not ig_code:
                continue
            if ig_code not in ig_map:
                ig_map[ig_code] = {
                    "ig_name": row["user_ig_link_user__ig__name"],
                    "ig_code": ig_code,
                    "members": 0,
                    "total_karma": 0,
                }
            ig_map[ig_code]["members"] += 1
            ig_map[ig_code]["total_karma"] += row["user_karma"] or 0

        return sorted(ig_map.values(), key=lambda item: item["members"], reverse=True)

    def _get_lc_details(self, org):
        learning_circles_qs = (
            LearningCircle.objects.filter(org=org)
            .annotate(
                members=Count(
                    "user_circle_link_circle",
                    filter=Q(user_circle_link_circle__accepted=True),
                )
            )
            .values("title", "ig__code", "ig__name", "members")
        )

        return [
            {
                "title": lc["title"] or "",
                "ig_code": lc["ig__code"],
                "ig_name": lc["ig__name"],
                "members": lc["members"],
            }
            for lc in learning_circles_qs
        ]
