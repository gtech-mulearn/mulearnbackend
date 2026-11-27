from io import BytesIO

import openpyxl
from django.db import transaction
from django.db.models import Count
from django.http import FileResponse
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from db.intern import InternTeam, UserInternTeamLink
from db.user import User, UserRoleLink
from utils.intern_permissions import (
    INACTIVE, INTERN_ROLE, LEAD_ROLE, MEMBER_ROLES, ON_LEAVE, OnboardError,
    actor_role, caller_team_id, change_end_date, change_status, current_membership, deactivate_membership,
    grant_roles, import_intern, is_admin, members_only, move_membership, onboard_intern,
    parse_date, promote_to_lead, remove_lead, scope_people, tenure_state, user_role_titles,
)
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import InternStatus, RoleType
from utils.utils import CommonUtils

from .serializers import (
    DeactivateInternSerializer, ManageInternSerializer, OnboardInternSerializer,
    ReassignInternsSerializer, UpdateInternSerializer, intern_queryset, intern_roles,
)
from .teams.teams_views import error_messages

MANAGE_ROLES = [RoleType.ADMIN.value, RoleType.INTERN_LEAD.value]
SEARCH_FIELDS = ['user__full_name', 'user__muid', 'team__name']
SORT_FIELDS = {'created_at': 'created_at', 'status': 'intern_status', 'full_name': 'user__full_name'}
LEAD_VALUES = {'yes': True, 'y': True, 'true': True, '1': True,
               'no': False, 'n': False, 'false': False, '0': False, '': False}

TEAM_ID_PARAM = OpenApiParameter(name='team_id', description='Admin only: limit to one team', required=False, type=str)
STATUS_PARAM = OpenApiParameter(name='status', description='ACTIVE, ON_LEAVE or INACTIVE', required=False, type=str)


def _failure(message):
    return CustomResponse(general_message=message).get_failure_response()


def _serialize(link_id):
    return ManageInternSerializer(intern_queryset().get(id=link_id)).data


def filtered_interns(request):
    """
    Interns the caller may see, with the list/export filters applied: current
    members only (Admin: every team; Lead: their own team).
    """
    admin = is_admin(request)
    qs = members_only(scope_people(intern_queryset(), request))

    team_id = request.query_params.get('team_id')
    if admin and team_id:
        qs = qs.filter(team_id=team_id)

    status = request.query_params.get('status')
    if status:
        qs = qs.filter(intern_status=status)
    return qs


def _team(team):
    return {"id": team.id, "name": team.name, "code": team.code}


def intern_detail(user, current):
    """One person: their current membership (or None) and the teams they were in before."""
    data = {"user": user.id, "full_name": user.full_name, "muid": user.muid, "current": None}
    if current:
        roles = [title for title in MEMBER_ROLES if title in user_role_titles(user.id, MEMBER_ROLES)]
        data["current"] = {
            "id": current.id,
            "team": _team(current.team),
            "status": current.intern_status,
            "status_reason": current.status_reason,
            "is_lead": LEAD_ROLE in roles,
            "roles": roles,
            "join_date": current.join_date,
            "end_date": current.end_date,
            "tenure_state": tenure_state(current),
            "joined_at": current.created_at,
        }
    ended = (
        UserInternTeamLink.objects.select_related('team')
        .filter(user_id=user.id, is_current=False).order_by('-updated_at')
    )
    data["previous_teams"] = [
        {"team": _team(link.team), "exit_reason": link.exit_reason,
         "join_date": link.join_date, "end_date": link.end_date,
         "joined_at": link.created_at, "left_at": link.updated_at}
        for link in ended
    ]
    return data


def locked_current_in_scope(request, user_id):
    """
    The person's current row, locked, if the caller may manage them (Admin: anyone;
    Lead: current members of their own team). None otherwise. Call inside atomic().
    """
    link = current_membership(user_id, lock=True)
    if not link:
        return None
    if not is_admin(request) and link.team_id != caller_team_id(request):
        return None
    return link


def lead_restriction(request, link):
    """A Lead may not act on another Lead or on themselves. Admins are not restricted."""
    if is_admin(request):
        return None
    if link.user_id == JWTUtils.fetch_user_id(request) or LEAD_ROLE in user_role_titles(link.user_id, [LEAD_ROLE]):
        return "Leads can't change another Lead or themselves."
    return None


class ManageInternAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(MANAGE_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "List interns (paginated): current members only (users holding Intern or Intern Lead). "
            "Admins see every team (optional team_id); an Intern Lead sees only their own team. "
            "With a user id (interns/<user_id>/): that person's current membership (null if they "
            "were deactivated) and the teams they were in before. Admin: anyone. Intern Lead: "
            "only current members of their own team."
        ),
        parameters=[TEAM_ID_PARAM, STATUS_PARAM],
        responses={200: ManageInternSerializer(many=True)},
    )
    def get(self, request, user_id=None):
        if user_id:
            user = User.every.filter(id=user_id).first()
            current = current_membership(user_id) if user else None
            if is_admin(request):
                found = user and UserInternTeamLink.objects.filter(user_id=user_id).exists()
            else:
                found = current and current.team_id == caller_team_id(request)
            if not found:
                return _failure("Intern not found.")
            return CustomResponse(response=intern_detail(user, current)).get_success_response()

        interns = filtered_interns(request).order_by('-created_at')
        paginated = CommonUtils.get_paginated_queryset(interns, request, SEARCH_FIELDS, SORT_FIELDS)
        serializer = ManageInternSerializer(paginated.get("queryset"), many=True)
        return CustomResponse(response={
            "data": serializer.data,
            "pagination": paginated.get("pagination"),
        }).get_success_response()

    @role_required(MANAGE_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Onboard a user as an intern in a team (Intern role only; Leads are made with PATCH "
            "is_lead). Admins can use any active team, an Intern Lead only their own. A deactivated "
            "user is brought back in the chosen team (their earlier row there is reopened if they "
            "were in it before). Refused for an active intern, or one marked INACTIVE (set their "
            "status to ACTIVE, or reassign them)."
        ),
        request=OnboardInternSerializer,
        responses={200: ManageInternSerializer},
    )
    def post(self, request, user_id=None):
        if user_id:
            return _failure("Onboard at interns/ without a user id. Use PATCH to update an intern.")

        serializer = OnboardInternSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message=error_messages(serializer.errors), response=serializer.errors
            ).get_failure_response()

        user = serializer.validated_data['user']
        team = serializer.validated_data['team']
        if not is_admin(request) and team.id != caller_team_id(request):
            return _failure("You can only onboard interns into your own team.")

        actor_id = JWTUtils.fetch_user_id(request)
        try:
            with transaction.atomic():
                link, _ = onboard_intern(
                    user, team, actor_id, role=actor_role(request),
                    join_date=serializer.validated_data['join_date'],
                    end_date=serializer.validated_data['end_date'],
                )
        except OnboardError as e:
            return _failure(str(e))

        return CustomResponse(
            general_message="Intern onboarded successfully.",
            response=_serialize(link.id),
        ).get_success_response()

    @role_required(MANAGE_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Make or remove a Lead: `{\"is_lead\": true | false}`, Admin only. Change the tenure "
            "end: `{\"end_date\": \"YYYY-MM-DD\"}`: Admin any date from today (extending a finished "
            "intern makes them ACTIVE again); Intern Lead only later, only for working interns of "
            "their team (not themselves or another Lead). Acts on the "
            "person's current membership (interns/<user_id>/); a deactivated intern can't be changed "
            "here: onboard them again. Change teams with interns/reassign/. `status`: ACTIVE or "
            "INACTIVE with a required `reason` (Admin, or a Lead for their own team); refused while "
            "the intern is ON_LEAVE, before their start date or after their tenure ended (extend "
            "the end date instead). ON_LEAVE only comes from approved leave. INACTIVE keeps the "
            "roles; the intern can't submit until set back to ACTIVE."
        ),
        request=UpdateInternSerializer,
        responses={200: ManageInternSerializer},
    )
    def patch(self, request, user_id=None):
        if not user_id:
            return _failure("A user id is required to update an intern.")
        if {'team_id', 'guild'} & set(request.data.keys()):
            return _failure("Use interns/reassign/ to change an intern's team.")
        if 'role' in request.data:
            return _failure("Use is_lead to make or remove a Lead.")
        serializer = UpdateInternSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message=error_messages(serializer.errors), response=serializer.errors
            ).get_failure_response()
        data = serializer.validated_data

        if 'is_lead' in data and not is_admin(request):
            return _failure("Only an admin can make or remove a Lead.")

        actor_id = JWTUtils.fetch_user_id(request)
        try:
            with transaction.atomic():
                link = locked_current_in_scope(request, user_id)
                if not link:
                    if is_admin(request) and UserInternTeamLink.objects.filter(user_id=user_id).exists():
                        return _failure("This intern was deactivated. Onboard them to bring them back.")
                    return _failure("Intern not found.")
                restriction = lead_restriction(request, link)
                if restriction:
                    return _failure(restriction)

                role = actor_role(request)
                if 'end_date' in data:
                    # Admin: any date from today, and extending a finished intern reactivates
                    # them. Lead: only later, only for working interns of their team.
                    change_end_date(link, data['end_date'], actor_id, role=role, admin=is_admin(request))

                if 'status' in data:
                    new_status = data['status']
                    # Raised, not returned: a return inside the transaction would commit
                    # the end_date change above while reporting a failure.
                    if link.intern_status == ON_LEAVE:
                        raise OnboardError(
                            "This intern is on approved leave; their status can't be changed until the leave ends."
                        )
                    state = tenure_state(link)
                    if state == 'UPCOMING':
                        raise OnboardError(f"This intern hasn't started yet (starts {link.join_date:%d %b %Y}).")
                    if state == 'ENDED':
                        raise OnboardError(
                            f"This intern's tenure ended on {link.end_date:%d %b %Y}. "
                            "Extend the end date to make them ACTIVE again, or deactivate them."
                        )
                    # Marking INACTIVE keeps the roles. A current row without an intern role
                    # (from before deactivation ended rows) gets the Intern role back.
                    if new_status != INACTIVE and not user_role_titles(link.user_id, MEMBER_ROLES):
                        grant_roles(link.user_id, [INTERN_ROLE], actor_id)
                    change_status(link, new_status, data.get('reason'), actor_id, role=role)

                if data.get('is_lead') is True:
                    # Raises (and rolls back the changes above) if the result is INACTIVE.
                    promote_to_lead(link, actor_id, role=role)
                elif data.get('is_lead') is False:
                    remove_lead(link, actor_id, role=role)

                link.updated_by_id = actor_id
                link.save(update_fields=[
                    'intern_status', 'previous_intern_status', 'status_reason', 'updated_by', 'updated_at',
                ])
        except OnboardError as e:
            return _failure(str(e))

        return CustomResponse(
            general_message="Intern details updated successfully.",
            response=_serialize(link.id),
        ).get_success_response()

    @role_required(MANAGE_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Deactivate an intern (remove them from the program): their membership ends "
            "(INACTIVE, not current) and both intern roles are removed. Body {\"reason\": \"...\"} "
            "is required and saved as exit_reason. Acts on the person's current membership "
            "(interns/<user_id>/). Admin: any intern. Intern Lead: own team, not another Lead or "
            "themselves. To bring them back, onboard them again."
        ),
        request=DeactivateInternSerializer,
        responses={200: OpenApiResponse(description="Intern deactivated successfully.")},
    )
    def delete(self, request, user_id=None):
        if not user_id:
            return _failure("A user id is required to deactivate an intern.")

        serializer = DeactivateInternSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message=error_messages(serializer.errors), response=serializer.errors
            ).get_failure_response()
        reason = serializer.validated_data['reason'].strip()

        actor_id = JWTUtils.fetch_user_id(request)
        with transaction.atomic():
            link = locked_current_in_scope(request, user_id)
            if not link:
                return _failure("Intern not found.")
            restriction = lead_restriction(request, link)
            if restriction:
                return _failure(restriction)
            deactivate_membership(link, actor_id, reason, role=actor_role(request))

        return CustomResponse(general_message="Intern deactivated successfully.").get_success_response()


class ManageInternReassignAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Reassign interns: `{user_ids (up to 200, from any teams), team_id, end_date}`, in one "
            "transaction. Each old row ends today; a new row starts today in the team with the "
            "given end_date, and the status moves with the intern (ON_LEAVE stays ON_LEAVE). "
            "Refused for interns who haven't started yet or whose tenure ended. "
            "Interns already in that team are skipped and listed in already_in_team. "
            "A reassigned Lead now leads the new team; they're listed in leads_moved."
        ),
        request=ReassignInternsSerializer,
        responses={200: OpenApiResponse(description="moved_count, already_in_team, leads_moved")},
    )
    def post(self, request):
        serializer = ReassignInternsSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message=error_messages(serializer.errors), response=serializer.errors
            ).get_failure_response()

        team = serializer.validated_data['team']
        user_ids = serializer.validated_data['user_ids']
        actor_id = JWTUtils.fetch_user_id(request)

        with transaction.atomic():
            # Lock every row of each person, then take their current row.
            # Sorted: every bulk operation locks users in the same order, so they can't deadlock.
            current = {user_id: current_membership(user_id, lock=True) for user_id in sorted(user_ids)}
            not_current = sorted(user_id for user_id, link in current.items() if link is None)
            if not_current:
                return CustomResponse(
                    general_message=(
                        "Some users aren't current interns (unknown, or deactivated), so they can't be "
                        "reassigned. Onboard deactivated interns into the team instead."
                    ),
                    response={"not_current_user_ids": not_current},
                ).get_failure_response()
            links = list(
                UserInternTeamLink.objects.select_related('team', 'user')
                .filter(id__in=[link.id for link in current.values()])
            )

            already = [link for link in links if link.team_id == team.id]
            to_move = [link for link in links if link.team_id != team.id]

            leads_moved = []
            if to_move:
                lead_user_ids = set(
                    UserRoleLink.objects
                    .filter(user_id__in=[link.user_id for link in to_move], role__title=LEAD_ROLE)
                    .values_list('user_id', flat=True)
                )
                try:
                    for link in to_move:
                        # Writes the REASSIGNED row in intern_history.
                        move_membership(
                            link, team, actor_id, role=actor_role(request),
                            end_date=serializer.validated_data['end_date'],
                        )
                except OnboardError as e:
                    transaction.set_rollback(True)
                    return _failure(str(e))
                leads_moved = [
                    {"full_name": link.user.full_name, "muid": link.user.muid, "from_team": link.team.name}
                    for link in to_move if link.user_id in lead_user_ids
                ]

        moved = len(to_move)
        message = (
            f"{moved} intern{'s' if moved != 1 else ''} reassigned to {team.name}."
            if moved else f"No interns reassigned; all are already in {team.name}."
        )
        return CustomResponse(
            general_message=message,
            response={
                "moved_count": moved,
                "already_in_team": [link.user.muid for link in already],
                "leads_moved": leads_moved,
            },
        ).get_success_response()


class ManageInternStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(MANAGE_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Intern counts by status. Counts members only (users holding Intern or Intern Lead). "
            "Admins see all teams (optional team_id); an Intern Lead sees their own team."
        ),
        parameters=[TEAM_ID_PARAM],
        responses={200: OpenApiResponse(description="Counts per status and total_interns.")},
    )
    def get(self, request):
        qs = members_only(scope_people(UserInternTeamLink.objects.all(), request))
        team_id = request.query_params.get('team_id')
        if team_id and is_admin(request):
            qs = qs.filter(team_id=team_id)

        data = {status.value: 0 for status in InternStatus}
        for row in qs.values('intern_status').annotate(count=Count('id')).order_by():
            data[row['intern_status']] = row['count']
        data['total_interns'] = sum(data.values())
        return CustomResponse(response=data).get_success_response()


class ManageInternExportAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(MANAGE_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Export interns as CSV. Same scope and filters as the intern list.",
        parameters=[TEAM_ID_PARAM, STATUS_PARAM],
        responses={200: OpenApiResponse(description="CSV attachment of interns.")},
    )
    def get(self, request):
        interns = filtered_interns(request).order_by('team__name', 'user__full_name')

        rows = [
            {
                'Full Name': link.user.full_name,
                'MuID': link.user.muid,
                'Team': link.team.name,
                'Team Code': link.team.code,
                'Lead': 'Yes' if LEAD_ROLE in intern_roles(link) else 'No',
                'Status': link.intern_status,
                'Join Date': link.join_date.isoformat() if link.join_date else '',
                'End Date': link.end_date.isoformat() if link.end_date else '',
                'Created At': link.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for link in interns
        ]
        return CommonUtils.generate_csv(rows, 'interns')


class ManageInternBulkImportTemplateAPIView(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(MANAGE_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Download the Excel template for bulk intern import. Sheet 'Interns' has the columns "
            "muid, team (team code) and lead (yes/no, optional). Sheet 'Teams' lists team names "
            "and codes: every team for an Admin, only their own team for an Intern Lead."
        ),
        responses={200: OpenApiResponse(description="Excel file download.")},
    )
    def get(self, request):
        teams = InternTeam.objects.filter(is_active=True).order_by('name')
        if not is_admin(request):
            teams = teams.filter(id=caller_team_id(request))

        wb = openpyxl.Workbook()
        interns_sheet = wb.active
        interns_sheet.title = "Interns"
        # join_date / end_date (YYYY-MM-DD) are required for new interns; not needed to promote.
        interns_sheet.append(['muid', 'team', 'lead', 'join_date', 'end_date'])

        teams_sheet = wb.create_sheet("Teams")
        teams_sheet.append(['name', 'code'])
        for name, code in teams.values_list('name', 'code'):
            teams_sheet.append([name, code])

        output = BytesIO()
        wb.save(output)
        output.seek(0)
        response = FileResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="intern_bulk_import_template.xlsx"'
        return response


class ManageInternBulkImportAPI(APIView):
    authentication_classes = [CustomizePermission]
    parser_classes = [MultiPartParser, FormParser]

    @role_required(MANAGE_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Bulk onboard interns from an Excel (.xlsx) file under 'excel_file'. Columns: 'muid', "
            "'team' (an existing team code) and optional 'lead' (yes/no). New or deactivated users "
            "are onboarded into the row's team (as Lead with lead=yes). An active intern in the "
            "same team with lead=yes is promoted to Lead; any other active intern is a failed row "
            "(use interns/reassign/ to move teams). The import never demotes a Lead. "
            "Intern Lead: every row must use their own team code and lead=yes is refused."
        ),
        responses={200: OpenApiResponse(
            description="success_count (onboarded + promoted), promoted_count, failed_count, failed_rows."
        )},
    )
    def post(self, request):
        actor_id = JWTUtils.fetch_user_id(request)
        admin = is_admin(request)
        own_team_id = None if admin else caller_team_id(request)
        if not admin and not own_team_id:
            return _failure("You aren't in a team, so you can't import interns.")

        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            return _failure("No file uploaded. Please attach an Excel file with key 'excel_file'.")
        if not excel_file.name.endswith('.xlsx'):
            return _failure("Invalid file type. Only .xlsx files are supported.")

        try:
            wb = openpyxl.load_workbook(excel_file, read_only=True)
        except Exception:
            return _failure("Could not read the uploaded file. Please ensure it is a valid .xlsx file.")

        ws = wb.worksheets[0]
        rows = ws.iter_rows(values_only=True)
        header_row = next(rows, None) or []
        headers = [str(h).strip().lower() if h is not None else None for h in header_row]

        missing = [h for h in ('muid', 'team') if h not in headers]
        if missing:
            return _failure(
                f"Missing required column(s): {', '.join(missing)}. "
                "Expected headers: muid, team, lead (optional), join_date, end_date."
            )
        muid_idx = headers.index('muid')
        team_idx = headers.index('team')
        lead_idx = headers.index('lead') if 'lead' in headers else None
        join_idx = headers.index('join_date') if 'join_date' in headers else None
        end_idx = headers.index('end_date') if 'end_date' in headers else None

        teams_by_code = {team.code.upper(): team for team in InternTeam.objects.filter(is_active=True)}
        success_count = 0
        promoted_count = 0
        failed_rows = []
        seen_muids = set()

        def cell(row, idx):
            if idx is None or idx >= len(row) or row[idx] is None:
                return ''
            return str(row[idx]).strip()

        def raw(row, idx):
            return None if idx is None or idx >= len(row) else row[idx]

        for row_num, row in enumerate(rows, start=2):
            muid, code, lead_raw = cell(row, muid_idx), cell(row, team_idx), cell(row, lead_idx)
            if not muid and not code and not lead_raw:
                continue

            def fail(reason):
                failed_rows.append({"row": row_num, "muid": muid or "(empty)", "reason": reason})

            if not muid or not code:
                fail("Both 'muid' and 'team' values are required.")
                continue
            if muid in seen_muids:
                fail("Duplicate muid in file — already processed earlier in this upload.")
                continue
            seen_muids.add(muid)

            make_lead = LEAD_VALUES.get(lead_raw.lower())
            if make_lead is None:
                fail(f"'lead' must be yes or no, not '{lead_raw}'.")
                continue
            if make_lead and not admin:
                fail("Only an admin can make a Lead.")
                continue
            team = teams_by_code.get(code.upper())
            if not team:
                fail(f"No team with code '{code}'.")
                continue
            if not admin and team.id != own_team_id:
                fail("You can only onboard interns into your own team.")
                continue
            join_raw, end_raw = raw(row, join_idx), raw(row, end_idx)
            join_date, end_date = parse_date(join_raw), parse_date(end_raw)
            if (join_raw not in (None, '') and join_date is None) or (end_raw not in (None, '') and end_date is None):
                fail("join_date and end_date must be dates (YYYY-MM-DD).")
                continue
            user = User.objects.filter(muid=muid).first()
            if not user:
                fail("No user found with this muid.")
                continue

            try:
                with transaction.atomic():
                    outcome = import_intern(
                        user, team, actor_id, make_lead=make_lead, role=actor_role(request),
                        join_date=join_date, end_date=end_date,
                    )
                success_count += 1
                if outcome == 'promoted':
                    promoted_count += 1
            except OnboardError as e:
                fail(str(e))
            except Exception as e:
                fail(f"Unexpected error: {str(e)}")

        return CustomResponse(
            general_message="Bulk intern import completed.",
            response={
                "success_count": success_count,
                "promoted_count": promoted_count,
                "failed_count": len(failed_rows),
                "failed_rows": failed_rows,
            },
        ).get_success_response()
