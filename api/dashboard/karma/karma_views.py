from django.db.models import Case, Count, F, IntegerField, Value, When
from django.db.models.functions import Coalesce, Floor
from rest_framework.views import APIView

from db.user import User
from utils.permission import CustomizePermission, role_required
from utils.response import CustomResponse
from utils.types import RoleType


class KarmaHistogramAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.ASSOCIATE.value])
    def get(self, request):
        student_karma_queryset = (
            User.objects.filter(user_role_link_user__role__title=RoleType.STUDENT.value)
            .distinct()
            .annotate(karma_value=Coalesce("wallet_user__karma", Value(0)))
            .annotate(
                karma_bucket=Case(
                    When(karma_value__lte=100, then=Value(0)),
                    default=Floor((F("karma_value") - Value(1)) / Value(100)),
                    output_field=IntegerField(),
                )
            )
            .values("karma_bucket")
            .annotate(users=Count("id"))
            .order_by("karma_bucket")
        )

        bucket_counts = {
            entry["karma_bucket"]: entry["users"] for entry in student_karma_queryset
        }

        if bucket_counts:
            max_bucket = max(bucket_counts.keys())
            ranges = []
            for bucket in range(max_bucket + 1):
                if bucket == 0:
                    range_label = "0-100"
                else:
                    range_label = f"{bucket * 100 + 1}-{(bucket + 1) * 100}"

                ranges.append(
                    {
                        "range": range_label,
                        "users": bucket_counts.get(bucket, 0),
                    }
                )
        else:
            ranges = []

        return CustomResponse(
            response={"ranges": ranges},
            general_message="Karma histogram fetched successfully",
        ).get_success_response()
