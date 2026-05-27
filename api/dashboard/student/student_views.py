from django.db.models import Count, ExpressionWrapper, F, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from rest_framework.views import APIView

from db.task import UserIgLink
from db.learning_circle import UserCircleLink
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType


class StudentParticipationBreakdownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.ASSOCIATE.value])
    def get(self, request):
        ig_count_queryset = (
            UserIgLink.objects.filter(user_id=OuterRef("pk"))
            .values("user_id")
            .annotate(total_igs=Count("ig", distinct=True))
            .values("total_igs")
        )

        circle_count_queryset = (
            UserCircleLink.objects.filter(user_id=OuterRef("pk"), accepted=True)
            .values("user_id")
            .annotate(total_circles=Count("circle", distinct=True))
            .values("total_circles")
        )

        students = (
            User.objects.filter(user_role_link_user__role__title=RoleType.STUDENT.value)
            .distinct()
            .select_related("wallet_user")
            .annotate(
                user_id=F("id"),
                karma=Coalesce("wallet_user__karma", Value(0)),
                ig_count=Coalesce(
                    Subquery(ig_count_queryset, output_field=IntegerField()), Value(0)
                ),
                circle_count=Coalesce(
                    Subquery(circle_count_queryset, output_field=IntegerField()), Value(0)
                ),
            )
            .annotate(
                total_participation=ExpressionWrapper(
                    F("ig_count") + F("circle_count"), output_field=IntegerField()
                )
            )
            .values(
                "user_id",
                "full_name",
                "karma",
                "ig_count",
                "circle_count",
                "total_participation",
            )
            .order_by("-karma", "full_name")
        )

        return CustomResponse(
            response={"students": list(students)},
            general_message="Student participation breakdown fetched successfully",
        ).get_success_response()
