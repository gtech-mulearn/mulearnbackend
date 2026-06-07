from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.db.models import Count, F, Sum, Q

from db.organization import Organization
from db.user import User
from db.task import InterestGroup
from db.learning_circle import LearningCircle

from utils.response import CustomResponse
from utils.types import OrganizationType

from api.dashboard.campus.serializers import CampusDetailsPublicSerializer

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
        org = Organization.objects.filter(code=college_code, org_type=OrganizationType.COLLEGE.value).first()
        if not org:
            return CustomResponse(general_message="College not found").get_failure_response()

        # 1. Basic Campus Details
        basic_campus_details = CampusDetailsPublicSerializer(org, many=False).data
        # Remove UUID and social_links
        basic_campus_details.pop("org_id", None)
        basic_campus_details.pop("social_links", None)

        # 2. All Students & Top 20 Leaderboard
        all_students_qs = (
            User.objects.filter(
                user_organization_link_user__org=org,
                user_organization_link_user__is_alumni=False
            )
            .annotate(
                karma=F("wallet_user__karma"),
                level=F("user_lvl_link_user__level__name")
            )
            .order_by("-karma", "-created_at")
            .values("full_name", "muid", "karma", "level")
        )

        all_students = []
        for index, student in enumerate(all_students_qs):
            all_students.append({
                "full_name": student["full_name"],
                "muid": student["muid"],
                "karma": student["karma"] or 0,
                "rank": index + 1,
                "level": student["level"]
            })

        top_20_leaderboard = all_students[:20]

        # 3. Active IGs
        active_igs_qs = (
            InterestGroup.objects.filter(
                user_ig_link_ig__user__user_organization_link_user__org=org,
                user_ig_link_ig__user__user_organization_link_user__verified=True,
                status="active"
            )
            .annotate(
                member_count=Count("user_ig_link_ig", filter=Q(user_ig_link_ig__user__user_organization_link_user__org=org), distinct=True)
            )
            .values("name", "code", "member_count")
        )

        active_igs = []
        for ig in active_igs_qs:
            active_igs.append({
                "ig_name": ig["name"],
                "ig_code": ig["code"],
                "member_count": ig["member_count"]
            })

        # 4. Learning Circles
        learning_circles_qs = (
            LearningCircle.objects.filter(org=org)
            .annotate(
                member_count=Count("user_circle_link_circle")
            )
            .values("title", "ig__name", "member_count")
        )

        learning_circles = []
        for lc in learning_circles_qs:
            learning_circles.append({
                "circle_name": lc["title"],
                "ig_name": lc["ig__name"],
                "member_count": lc["member_count"]
            })

        return CustomResponse(
            response={
                "basic_campus_details": basic_campus_details,
                "all_students": all_students,
                "top_20_leaderboard": top_20_leaderboard,
                "active_igs": active_igs,
                "learning_circles": learning_circles
            }
        ).get_success_response()
