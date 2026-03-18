from datetime import datetime

from django.db.models import Count, Sum, Q
from django.db.models.functions import Coalesce
from rest_framework.views import APIView

from db.task import InterestGroup, KarmaActivityLog
from utils.permission import CustomizePermission
from utils.permission import JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, WebHookActions, WebHookCategory
from utils.utils import CommonUtils, DiscordWebhooks
from .dash_ig_serializer import (
    InterestGroupSerializer,
    InterestGroupCreateUpdateSerializer,
    IGTaskSummarySerializer,
)
import json
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from api.dashboard.roles.dash_roles_serializer import RoleDashboardSerializer
from db.user import Role


class InterestGroupAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        ig_queryset = (
            InterestGroup.objects.select_related("created_by", "updated_by")
            .prefetch_related("user_ig_link_ig")
            .annotate(members=Count("user_ig_link_ig"))
            .all()
        )
        paginated_queryset = CommonUtils.get_paginated_queryset(
            ig_queryset,
            request,
            [
                "name",
                "created_by__full_name",
                "updated_by__full_name",
            ],
            {
                "name": "name",
                "members": "members",
                "updated_on": "updated_at",
                "updated_by": "updated_by__full_name",
                "created_on": "created_at",
                "created_by": "created_by__full_name",
            },
        )

        ig_serializer_data = InterestGroupSerializer(
            paginated_queryset.get("queryset"), many=True
        ).data

        return CustomResponse().paginated_response(
            data=ig_serializer_data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        request_data = request.data

        # serialize JSON-able fields to strings for DB storage
        for fld in [
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
        ]:
            if fld in request_data and not isinstance(request_data.get(fld), str):
                try:
                    request_data[fld] = json.dumps(request_data.get(fld))
                except Exception:
                    pass

        request_data["created_by"] = request_data["updated_by"] = user_id

        serializer = InterestGroupCreateUpdateSerializer(
            data=request_data,
        )

        if serializer.is_valid():
            serializer.save()

            role_serializer = RoleDashboardSerializer(
                data={
                    "title": request_data.get("name"),
                    "description": request_data.get("name") + " Interest Group Member",
                    "created_by": request_data.get("created_by"),
                    "updated_by": request_data.get("updated_by"),
                },
                context={"request": request},
            )

            if role_serializer.is_valid():
                role_serializer.save()
            else:
                return CustomResponse(
                    general_message=role_serializer.errors
                ).get_failure_response()

            campus_role_serializer = RoleDashboardSerializer(
                data={
                    "title": RoleType.IG_CAMPUS_LEAD_ROLE(request_data.get("code")),
                    "description": request_data.get("name")
                    + " Intrest Group Campus Lead",
                    "created_by": request_data.get("created_by"),
                    "updated_by": request_data.get("updated_by"),
                },
                context={"request": request},
            )

            if campus_role_serializer.is_valid():
                campus_role_serializer.save()
            else:
                return CustomResponse(
                    general_message=campus_role_serializer.errors
                ).get_failure_response()

            ig_lead_role_serializer = RoleDashboardSerializer(
                data={
                    "title": RoleType.IG_LEAD_ROLE(request_data.get("code")),
                    "description": request_data.get("name") + " Interest Group Lead",
                    "created_by": request_data.get("created_by"),
                    "updated_by": request_data.get("updated_by"),
                },
                context={"request": request},
            )

            if ig_lead_role_serializer.is_valid():
                ig_lead_role_serializer.save()
            else:
                return CustomResponse(
                    general_message=ig_lead_role_serializer.errors
                ).get_failure_response()

            DiscordWebhooks.general_updates(
                WebHookCategory.INTEREST_GROUP.value,
                WebHookActions.CREATE.value,
                request_data.get("name"),
                request_data.get("code"),
            )

            return CustomResponse(
                response={"interestGroup": serializer.data}
            ).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        ig = InterestGroup.objects.get(id=pk)

        ig_old_name = ig.name
        ig_old_code = ig.code

        request_data = request.data
        for fld in [
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
        ]:
            if fld in request_data and not isinstance(request_data.get(fld), str):
                try:
                    request_data[fld] = json.dumps(request_data.get(fld))
                except Exception:
                    pass
        request_data["updated_by"] = user_id

        serializer = InterestGroupCreateUpdateSerializer(
            data=request_data, instance=ig, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            ig_new_name = ig.name
            ig_new_code = ig.code

            ig_role = Role.objects.filter(title=ig_old_name).first()

            if ig_role:
                ig_role.title = ig_new_name
                ig_role.description = ig_new_name + " Interest Group Member"
                ig_role.save()

            ig_campus_lead_role = Role.objects.filter(
                title=RoleType.IG_CAMPUS_LEAD_ROLE(ig_old_code)
            ).first()

            if ig_campus_lead_role:
                ig_campus_lead_role.title = ig_new_code + " CampusLead"
                ig_campus_lead_role.description = (
                    ig_new_name + " Interest Group Campus Lead"
                )
                ig_campus_lead_role.save()

            ig_lead_role = Role.objects.filter(
                title=RoleType.IG_LEAD_ROLE(ig_old_code)
            ).first()

            if ig_lead_role:
                ig_lead_role.title = RoleType.IG_LEAD_ROLE(ig_new_code)
                ig_lead_role.description = ig_new_name + " Interest Group Lead"
                ig_lead_role.save()

            DiscordWebhooks.general_updates(
                WebHookCategory.INTEREST_GROUP.value,
                WebHookActions.EDIT.value,
                ig_new_name,
                ig_new_code,
                ig_old_name,
                ig_old_code,
            )
            return CustomResponse(
                response={"interestGroup": serializer.data}
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, pk):
        ig = InterestGroup.objects.filter(id=pk).first()

        if ig is None:
            return CustomResponse(general_message="invalid ig").get_success_response()
        ig_role = Role.objects.filter(title=ig.name).first()
        if ig_role:
            ig_role.delete()
        ig_campus_role = Role.objects.filter(
            title=RoleType.IG_CAMPUS_LEAD_ROLE(ig.code)
        ).first()
        if ig_campus_role:
            ig_campus_role.delete()
        ig_lead_role = Role.objects.filter(title=RoleType.IG_LEAD_ROLE(ig.code)).first()
        if ig_lead_role:
            ig_lead_role.delete()
        ig.delete()

        DiscordWebhooks.general_updates(
            WebHookCategory.INTEREST_GROUP.value,
            WebHookActions.DELETE.value,
            ig.name,
            ig.code,
        )
        return CustomResponse(
            general_message="ig deleted successfully"
        ).get_success_response()


class InterestGroupCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        ig_serializer = (
            InterestGroup.objects.select_related("created_by", "updated_by")
            .prefetch_related("user_ig_link_ig")
            .annotate(members=Count("user_ig_link_ig"))
            .all()
        )

        ig_serializer_data = InterestGroupSerializer(ig_serializer, many=True).data

        return CommonUtils.generate_csv(ig_serializer_data, "Interest Group")


class InterestGroupGetAPI(APIView):
    authentication_classes = [CustomizePermission]
    @role_required([RoleType.ADMIN.value])
    def get(self, request, pk):
        ig_data = InterestGroup.objects.filter(id=pk).first()

        if not ig_data:
            return CustomResponse(
                general_message="Interest Group Does Not Exist"
            ).get_failure_response()

        serializer = InterestGroupSerializer(ig_data, many=False)

        return CustomResponse(
            response={"interestGroup": serializer.data}
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, pk):
        """Allow IG Lead or Admin to update IG editable fields."""
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        ig = InterestGroup.objects.filter(id=pk).first()
        if not ig:
            return CustomResponse(general_message="Interest Group Does Not Exist").get_failure_response()

        # Permission: Admins or IG Lead role for this IG code
        ig_lead_role_title = RoleType.IG_LEAD_ROLE(ig.code)
        if (RoleType.ADMIN.value not in roles) and (ig_lead_role_title not in roles):
            return CustomResponse(general_message="You do not have permission to update this Interest Group").get_failure_response()

        request_data = request.data
        for fld in [
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
        ]:
            if fld in request_data and not isinstance(request_data.get(fld), str):
                try:
                    request_data[fld] = json.dumps(request_data.get(fld))
                except Exception:
                    pass
        request_data["updated_by"] = user_id

        serializer = InterestGroupCreateUpdateSerializer(data=request_data, instance=ig, partial=True)

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response={"interestGroup": serializer.data}).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()


class InterestGroupListApi(APIView):
    @method_decorator(cache_page(60 * 10))
    def get(self, request):
        ig = (
            InterestGroup.objects.all()
            .select_related("created_by", "updated_by")
            .prefetch_related("user_ig_link_ig")
            .annotate(members=Count("user_ig_link_ig"))
        )

        serializer = InterestGroupSerializer(ig, many=True)

        return CustomResponse(
            response={"interestGroup": serializer.data}
        ).get_success_response()


class IGTaskSummaryAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([
        RoleType.ADMIN.value,
        RoleType.FELLOW.value,
        RoleType.ASSOCIATE.value,
    ])
    def get(self, request, ig_id):
        ig = (
            InterestGroup.objects.filter(id=ig_id)
            .values("id", "name", "code")
            .first()
        )

        if not ig:
            return CustomResponse(
                general_message="Interest Group not found"
            ).get_failure_response(status_code=404, http_status_code=404)

        from_param = request.query_params.get("from_date")
        to_param = request.query_params.get("to_date")
        from_date = self._parse_date(from_param) if from_param else None
        if from_param and from_date is None:
            return CustomResponse(
                general_message="Invalid date format. Use YYYY-MM-DD"
            ).get_failure_response()
        to_date = self._parse_date(to_param) if to_param else None
        if to_param and to_date is None:
            return CustomResponse(
                general_message="Invalid date format. Use YYYY-MM-DD"
            ).get_failure_response()

        if from_date and to_date and from_date > to_date:
            return CustomResponse(
                general_message="from_date cannot be after to_date"
            ).get_failure_response()

        filters = Q(task__ig_id=ig_id)
        if from_date:
            filters &= Q(created_at__date__gte=from_date)
        if to_date:
            filters &= Q(created_at__date__lte=to_date)

        activity_qs = KarmaActivityLog.objects.filter(filters)
        summary_values = activity_qs.aggregate(
            total_tasks=Count("id"),
            total_karma=Coalesce(Sum("karma"), 0),
            unique_contributors=Count("user", distinct=True),
        )

        top_contributors_queryset = (
            activity_qs.filter(user__isnull=False)
            .values("user__full_name", "user__muid")
            .annotate(karma_earned=Coalesce(Sum("karma"), 0))
            .order_by("-karma_earned", "user__full_name")[:5]
        )
        top_contributors = [
            {
                "full_name": entry["user__full_name"],
                "muid": entry["user__muid"],
                "karma_earned": entry["karma_earned"],
            }
            for entry in top_contributors_queryset
        ]

        serializer = IGTaskSummarySerializer(
            data={
                "ig_id": ig["id"],
                "ig_name": ig["name"],
                "ig_code": ig["code"],
                "total_tasks_completed": summary_values.get("total_tasks", 0) or 0,
                "total_karma_awarded": summary_values.get("total_karma", 0) or 0,
                "unique_contributors": summary_values.get("unique_contributors", 0) or 0,
                "top_contributors": top_contributors,
                "date_range": {
                    "from_date": from_date,
                    "to_date": to_date,
                },
            }
        )
        serializer.is_valid(raise_exception=True)

        return CustomResponse(
            response=serializer.data,
            general_message="Task summary fetched successfully",
        ).get_success_response()

    @staticmethod
    def _parse_date(value: str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
