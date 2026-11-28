from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.views import APIView

from db.intern import UserInternTeamLink
from utils.intern_permissions import (
    INACTIVE, LEAD_ROLE, active_teams, current_membership, holds_role_subquery, in_tenure, members_only,
    working_membership_error,
)
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils


class InternTeamMembersAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "The caller's own team and its members (paginated), with who the Leads are. "
            "Only members who aren't INACTIVE are listed."
        ),
        responses={200: OpenApiResponse(description="team, data and pagination.")},
    )
    def get(self, request):
        own = current_membership(JWTUtils.fetch_user_id(request))
        error = working_membership_error(own)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        members = (
            in_tenure(members_only(UserInternTeamLink.objects.filter(team_id=own.team_id)))
            .exclude(intern_status=INACTIVE)
            .select_related('user')
            .annotate(is_lead=holds_role_subquery([LEAD_ROLE]))
            .order_by('user__full_name')
        )
        paginated = CommonUtils.get_paginated_queryset(
            members, request,
            ['user__full_name', 'user__muid'],
            {'full_name': 'user__full_name'},
        )
        data = [
            {
                "full_name": link.user.full_name,
                "muid": link.user.muid,
                "profile_pic": link.user.profile_pic,
                "is_lead": link.is_lead,
            }
            for link in paginated.get("queryset")
        ]
        return CustomResponse(response={
            "team": {"id": own.team.id, "name": own.team.name, "code": own.team.code},
            "data": data,
            "pagination": paginated.get("pagination"),
        }).get_success_response()


class InternTeamListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value, RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Every active intern team as {id, name, code}, sorted by name, for dropdowns. Replaces intern/guilds/.",
        responses={200: OpenApiResponse(description="List of active teams.")},
    )
    def get(self, request):
        # Teams are a small, admin-created set, so this dropdown list is not paginated.
        teams = list(active_teams().order_by('name').values('id', 'name', 'code'))
        return CustomResponse(response=teams).get_success_response()
