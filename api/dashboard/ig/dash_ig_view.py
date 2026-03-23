from datetime import datetime

from django.db.models import Count, Sum
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
    InterestGroupRequestSerializer,
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
                "status": "status",
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


class InterestGroupRequestAPI(APIView):
    """API endpoint for users to submit and retrieve IG creation requests."""
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.COMPANY.value])
    def get(self, request):
        """Retrieve Interest Group requests created by a company user.
        
        Query Parameters:
            - user_id (optional): Filter by specific company user ID. 
              If not provided, defaults to the authenticated user's ID.
              Only admins can query other users' requests.
            - status (optional): Filter by IG status (requested, active, rejected, cancelled)
        """
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)
        target_user_id = request.query_params.get('user_id')
        status_filter = request.query_params.get('status')
        is_admin = RoleType.ADMIN.value in roles

        ig_queryset = InterestGroup.objects.select_related(
            "created_by", "updated_by"
        ).prefetch_related(
            "user_ig_link_ig"
        )
        
        if target_user_id:
            if target_user_id != user_id and not is_admin:
                return CustomResponse(
                    general_message="You can only view your own IG requests"
                ).get_failure_response()
            ig_queryset = ig_queryset.filter(created_by_id=target_user_id)
        else:
            if not is_admin:
                ig_queryset = ig_queryset.filter(created_by_id=user_id)

        if status_filter:
            valid_statuses = ['active', 'requested', 'cancelled', 'rejected']
            if status_filter not in valid_statuses:
                return CustomResponse(
                    general_message=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                ).get_failure_response()
            ig_queryset = ig_queryset.filter(status=status_filter)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            ig_queryset,
            request,
            ["name", "code", "category"],
            {
                "name": "name",
                "status": "status",
                "ig_name": "name",
                "user_full_name": "created_by__full_name",
                "created_at": "created_at",
                "created_on": "created_at",
                "updated_on": "updated_at",
            },
        )

        ig_serializer_data = InterestGroupSerializer(
            paginated_queryset.get("queryset"), many=True
        ).data
        
        return CustomResponse().paginated_response(
            data=ig_serializer_data, 
            pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value, RoleType.COMPANY.value])
    def post(self, request):
        """Submit a new Interest Group creation request."""
        user_id = JWTUtils.fetch_user_id(request)

        request_data = request.data.copy()

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
        request_data["status"] = "requested"

        serializer = InterestGroupRequestSerializer(data=request_data)

        if serializer.is_valid():
            ig_instance = serializer.save(
                created_by_id=user_id,
                updated_by_id=user_id,
                status="requested"
            )
            response_serializer = InterestGroupSerializer(ig_instance)
            
            return CustomResponse(
                response={"interestGroup": response_serializer.data},
                general_message="Interest Group request submitted successfully. It will be reviewed by admins."
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, pk):
        """Update Interest Group request status (Admin only).
        
        Allowed status transitions:
            - requested → active
            - requested → rejected
            - requested → cancelled
            - any status → any status (admin override)
        """
        user_id = JWTUtils.fetch_user_id(request)
        
        try:
            ig = InterestGroup.objects.get(id=pk)
        except InterestGroup.DoesNotExist:
            return CustomResponse(
                general_message="Interest Group not found"
            ).get_failure_response()

        new_status = request.data.get('status')

        valid_statuses = ['active', 'requested', 'cancelled', 'rejected']
        if not new_status:
            return CustomResponse(
                general_message="Status field is required"
            ).get_failure_response()
        
        if new_status not in valid_statuses:
            return CustomResponse(
                general_message=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            ).get_failure_response()

        ig.status = new_status
        ig.updated_by_id = user_id
        ig.save()

        response_serializer = InterestGroupSerializer(ig)
        
        return CustomResponse(
            response={"interestGroup": response_serializer.data},
            general_message=f"Interest Group status updated to '{new_status}'"
        ).get_success_response()



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

    @role_required([RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.ASSOCIATE.value])
    def get(self, request, ig_id):
        """Return a task activity summary for a given Interest Group.

        Supports optional date range filtering via `from_date` and `to_date`
        query params (format: YYYY-MM-DD). Returns aggregate zeros — not a
        failure — when there is no activity in the requested range.
        """
        ig = InterestGroup.objects.filter(id=ig_id).first()
        if not ig:
            return CustomResponse(
                general_message="Interest Group not found"
            ).get_failure_response()

        from_date_str = request.query_params.get("from_date")
        to_date_str = request.query_params.get("to_date")

        from_date = None
        to_date = None

        try:
            if from_date_str:
                from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
            if to_date_str:
                to_date = datetime.strptime(to_date_str, "%Y-%m-%d")
        except ValueError:
            return CustomResponse(
                general_message="Invalid date format. Use YYYY-MM-DD"
            ).get_failure_response()

        logs = KarmaActivityLog.objects.filter(
            task__ig=ig,
            user__isnull=False,
        ).select_related("user", "task")

        if from_date:
            logs = logs.filter(created_at__date__gte=from_date.date())
        if to_date:
            logs = logs.filter(created_at__date__lte=to_date.date())

        totals = logs.aggregate(
            total_tasks_completed=Count("id"),
            total_karma_awarded=Sum("karma"),
            unique_contributors=Count("user", distinct=True),
        )

        top_contributors = [
            {
                "full_name": row["user__full_name"],
                "muid": row["user__muid"],
                "karma_earned": row["karma_earned"],
            }
            for row in (
                logs.values("user__full_name", "user__muid")
                .annotate(karma_earned=Sum("karma"))
                .order_by("-karma_earned")[:5]
            )
        ]

        serializer = IGTaskSummarySerializer(data={
            "ig_id": ig.id,
            "ig_name": ig.name,
            "ig_code": ig.code,
            "total_tasks_completed": totals["total_tasks_completed"] or 0,
            "total_karma_awarded": totals["total_karma_awarded"] or 0,
            "unique_contributors": totals["unique_contributors"] or 0,
            "top_contributors": top_contributors,
            "date_range": {
                "from_date": from_date_str,
                "to_date": to_date_str,
            },
        })
        serializer.is_valid(raise_exception=True)

        return CustomResponse(
            general_message="Task summary fetched successfully",
            response=serializer.validated_data,
        ).get_success_response()