from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, Value
from django.db.models.functions import Least
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.views import APIView

from db.intern import InternTeam, UserInternTeamLink
from utils.intern_permissions import (
    INACTIVE, LEAD_ROLE, MEMBER_ROLES, caller_team_id, holds_role_subquery, is_admin, ist_today,
)
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from .serializers import InternTeamSerializer, InternTeamWriteSerializer

# Only an admin may change these; a Lead may edit their own team's description.
ADMIN_ONLY_FIELDS = {'name', 'code'}
# exit_reason on the leftover rows ended when their team is deactivated.
EXIT_REASON_TEAM_DEACTIVATED = "Team deactivated"

SEARCH_FIELDS = ['name', 'code']
SORT_FIELDS = {'name': 'name', 'code': 'code', 'created_at': 'created_at'}

INCLUDE_INACTIVE_PARAM = OpenApiParameter(
    name='include_inactive', description='Admin only: true also lists inactive teams', required=False, type=str,
)


def annotate_counts(queryset):
    """
    Adds member_count and active_member_count in the same query. Members are
    current rows whose person holds an intern role; ended rows are history. The
    role join can match a member more than once, so the counts are distinct.
    """
    holds_role = Q(members__is_current=True, members__user__user_role_link_user__role__title__in=MEMBER_ROLES)
    return queryset.annotate(
        member_count=Count('members', filter=holds_role, distinct=True),
        active_member_count=Count(
            'members', filter=holds_role & ~Q(members__intern_status=INACTIVE), distinct=True,
        ),
    )


def leads_by_team(team_ids):
    """One query for the Leads of every team on the page: {team_id: [lead, ...]}."""
    links = (
        UserInternTeamLink.objects
        .filter(team_id__in=team_ids, is_current=True)
        .filter(holds_role_subquery([LEAD_ROLE]))
        .select_related('user')
        .order_by('user__full_name')
    )
    result = {}
    for link in links:
        result.setdefault(link.team_id, []).append({
            "full_name": link.user.full_name,
            "muid": link.user.muid,
            "profile_pic": link.user.profile_pic,
        })
    return result


def serialize_team(team_id):
    team = annotate_counts(InternTeam.objects.filter(id=team_id)).first()
    if not team:
        return None
    return InternTeamSerializer(team, context={'leads_by_team': leads_by_team([team.id])}).data


def error_messages(errors):
    """Flattens DRF serializer errors into a list of plain messages."""
    messages = []
    for value in errors.values():
        if isinstance(value, (list, tuple)):
            messages.extend(str(v) for v in value)
        else:
            messages.append(str(value))
    return messages


def _failure(message, status_code=400):
    return CustomResponse(general_message=message).get_failure_response(
        status_code=status_code, http_status_code=status_code
    )


class InternTeamAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "List intern teams (paginated). Admin: every active team; include_inactive=true also "
            "lists inactive ones. Intern Lead: only their own team. One team by id (teams/<id>/) "
            "is Admin only. `member_count` counts current members (holding Intern or Intern Lead); "
            "`active_member_count` leaves out those marked INACTIVE. `leads` lists current members "
            "holding Intern Lead."
        ),
        parameters=[
            OpenApiParameter(name='search', description='Match name or code', required=False, type=str),
            OpenApiParameter(name='sortBy', description='name, code or created_at; prefix - for descending', required=False, type=str),
            INCLUDE_INACTIVE_PARAM,
        ],
        responses={200: InternTeamSerializer(many=True)},
    )
    def get(self, request, team_id=None):
        admin = is_admin(request)
        if team_id:
            if not admin:
                return _failure("Only an admin can view a team by id. Use teams/ to see your own team.")
            data = serialize_team(team_id)
            if data is None:
                return _failure("Team not found.")
            return CustomResponse(response=data).get_success_response()

        if admin:
            teams = InternTeam.objects.all()
            if request.query_params.get('include_inactive', '').lower() not in ('true', '1'):
                teams = teams.filter(is_active=True)
        else:
            # A Lead's current team is always active: a team with members can't be deactivated.
            teams = InternTeam.objects.filter(id=caller_team_id(request))

        teams = annotate_counts(teams).order_by('name')
        paginated = CommonUtils.get_paginated_queryset(teams, request, SEARCH_FIELDS, SORT_FIELDS)
        page = list(paginated.get("queryset"))
        serializer = InternTeamSerializer(
            page, many=True, context={'leads_by_team': leads_by_team([t.id for t in page])}
        )
        return CustomResponse(response={
            "data": serializer.data,
            "pagination": paginated.get("pagination"),
        }).get_success_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Create an intern team. The name can repeat; the code must be unique across every "
            "team, active or inactive (ignoring case), and is saved in uppercase."
        ),
        request=InternTeamWriteSerializer,
        responses={200: InternTeamSerializer},
    )
    def post(self, request, team_id=None):
        if team_id:
            return _failure("Create a team at teams/ without a team id. Use PATCH to edit a team.")

        serializer = InternTeamWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message=error_messages(serializer.errors), response=serializer.errors
            ).get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)
        try:
            team = serializer.save(created_by_id=user_id, updated_by_id=user_id)
        except IntegrityError:
            # Two creates raced past the uniqueness check; the unique code key let one through.
            return _failure("A team with this code already exists.")

        return CustomResponse(
            general_message="Team created successfully.",
            response=serialize_team(team.id),
        ).get_success_response()

    @role_required([RoleType.ADMIN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Edit a team. Admins can change name, code and description of any team, active or "
            "inactive. An Intern Lead can change only the description, and only of their own team."
        ),
        request=InternTeamWriteSerializer,
        responses={200: InternTeamSerializer},
    )
    def patch(self, request, team_id=None):
        if not team_id:
            return _failure("A team id is required to edit a team.")

        team = InternTeam.objects.filter(id=team_id).first()
        if not team:
            return _failure("Team not found.")

        user_id = JWTUtils.fetch_user_id(request)
        if not is_admin(request):
            if ADMIN_ONLY_FIELDS & set(request.data.keys()):
                return _failure("Only an admin can change a team's name or code.")
            if caller_team_id(request) != team.id:
                return _failure("You can only edit your own team.")

        serializer = InternTeamWriteSerializer(team, data=request.data, partial=True)
        if not serializer.is_valid():
            return CustomResponse(
                general_message=error_messages(serializer.errors), response=serializer.errors
            ).get_failure_response()

        try:
            serializer.save(updated_by_id=user_id)
        except IntegrityError:
            return _failure("A team with this code already exists.")

        return CustomResponse(
            general_message="Team updated successfully.",
            response=serialize_team(team.id),
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Deactivate a team (teams are never deleted). Refused with 409 while the team has "
            "current members, including members marked INACTIVE: reassign them first. Leftover "
            "current rows of people without an intern role are ended. The team's history "
            "(memberships, timesheets, reviews, tasks, leave) is kept. Activate it again with "
            "teams/<id>/activate/."
        ),
        responses={
            200: OpenApiResponse(description="ended_memberships: leftover rows ended."),
            409: OpenApiResponse(description="The team still has members."),
        },
    )
    def delete(self, request, team_id=None):
        if not team_id:
            return _failure("A team id is required to deactivate a team.")

        actor_id = JWTUtils.fetch_user_id(request)
        with transaction.atomic():
            team = InternTeam.objects.select_for_update().filter(id=team_id).first()
            if not team:
                return _failure("Team not found.")
            if not team.is_active:
                return _failure("Team is already inactive.")

            current = UserInternTeamLink.objects.select_for_update().filter(team=team, is_current=True)
            member_count = current.filter(holds_role_subquery(MEMBER_ROLES)).count()
            if member_count:
                noun = "member" if member_count == 1 else "members"
                return CustomResponse(
                    general_message=(
                        f"This team still has {member_count} {noun}. "
                        "Reassign them before deactivating it."
                    ),
                    response={"member_count": member_count},
                ).get_failure_response(status_code=409, http_status_code=409)

            # Nobody's current row may point at an inactive team.
            # end_date becomes the actual last day (today), unless the tenure already ended.
            today = ist_today()
            ended = current.update(
                intern_status=INACTIVE, is_current=False, exit_reason=EXIT_REASON_TEAM_DEACTIVATED,
                end_date=Least(F('end_date'), Value(today)),
                updated_by_id=actor_id, updated_at=timezone.now(),
            )
            team.is_active = False
            team.deactivated_at = timezone.now()
            team.deactivated_by_id = actor_id
            team.updated_by_id = actor_id
            team.save(update_fields=['is_active', 'deactivated_at', 'deactivated_by', 'updated_by', 'updated_at'])

        return CustomResponse(
            general_message="Team deactivated.",
            response={"ended_memberships": ended},
        ).get_success_response()


class InternTeamActivateAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Activate an inactive team. Nobody is added back automatically: onboard or reassign "
            "interns into it."
        ),
        responses={200: InternTeamSerializer},
    )
    def post(self, request, team_id):
        actor_id = JWTUtils.fetch_user_id(request)
        with transaction.atomic():
            team = InternTeam.objects.select_for_update().filter(id=team_id).first()
            if not team:
                return _failure("Team not found.")
            if team.is_active:
                return _failure("Team is already active.")
            team.is_active = True
            team.deactivated_at = None
            team.deactivated_by = None
            team.updated_by_id = actor_id
            team.save(update_fields=['is_active', 'deactivated_at', 'deactivated_by', 'updated_by', 'updated_at'])

        return CustomResponse(
            general_message="Team activated.",
            response=serialize_team(team.id),
        ).get_success_response()
