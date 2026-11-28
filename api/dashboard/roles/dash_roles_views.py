import uuid
from django.db import IntegrityError, transaction
from rest_framework.views import APIView

from db.intern import InternTeam
from db.user import Role, User, UserRoleLink
from utils.intern_permissions import (
    MEMBER_ROLES, OnboardError, deactivate_members, import_intern, parse_date, record_lead_removed,
)
from utils.permission import CustomizePermission, role_required, JWTUtils
from utils.response import CustomResponse
from utils.types import InternActorRole, RoleType, WebHookActions, WebHookCategory
from utils.utils import CommonUtils, DateTimeUtils, DiscordWebhooks, ImportCSV
from . import dash_roles_serializer

from openpyxl import load_workbook
from tempfile import NamedTemporaryFile
from io import BytesIO
from django.http import FileResponse
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema, OpenApiResponse


class RoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Roles'],
        description="Retrieve Role.",
        responses={200: dash_roles_serializer.RoleDashboardSerializer},
    )
    def get(self, request):
        # created_by / updated_by names are read for every row.
        roles_queryset = Role.objects.select_related("created_by", "updated_by")

        queryset = CommonUtils.get_paginated_queryset(
            roles_queryset,
            request,
            [
                "id",
                "title",
                "description",
                "updated_by__full_name",
                "created_by__full_name",
            ],
            {
                "title": "title",
                "description": "description",
                "members": "userrolelink",
                "updated_by": "updated_by__full_name",
                "created_by": "created_by__full_name",
                "updated_at": "updated_at",
                "created_at": "created_at",
            },
        )

        # Verified member counts for the page in one grouped query. Done after
        # pagination so the paginator's COUNT stays a plain COUNT(*).
        page = list(queryset.get("queryset"))
        member_counts = dict(
            UserRoleLink.objects.filter(
                role_id__in=[role.id for role in page], verified=True
            )
            .values_list("role_id")
            .annotate(total=Count("id"))
        )
        for role in page:
            role.verified_member_count = member_counts.get(role.id, 0)

        serializer = dash_roles_serializer.RoleDashboardSerializer(page, many=True)

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Roles'],
        description="Partially update Role.",
        responses={200: dash_roles_serializer.RoleDashboardSerializer},
    )
    def patch(self, request, roles_id):
        role = Role.objects.get(id=roles_id)
        old_name = role.title

        serializer = dash_roles_serializer.RoleDashboardSerializer(
            role, data=request.data, partial=True, context={"request": request}
        )

        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        try:
            serializer.save()
            newname = role.title

            DiscordWebhooks.general_updates(
                WebHookCategory.ROLE.value, WebHookActions.EDIT.value, newname, old_name
            )

            return CustomResponse(
                response={"data": serializer.data}
            ).get_success_response()

        except IntegrityError as e:
            return CustomResponse(
                general_message="Database integrity error",
            ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Roles'], description="Delete Role.",
        responses={200: dash_roles_serializer.RoleDashboardSerializer},
    )
    def delete(self, request, roles_id):
        role = Role.objects.get(id=roles_id)
        role.delete()

        DiscordWebhooks.general_updates(
            WebHookCategory.ROLE.value, WebHookActions.DELETE.value, role.title
        )
        return CustomResponse(
            general_message="Role deleted successfully"
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Roles'],
        description="Create Role.",
        request=dash_roles_serializer.RoleDashboardSerializer,
        responses={200: dash_roles_serializer.RoleDashboardSerializer},
    )
    def post(self, request):
        serializer = dash_roles_serializer.RoleDashboardSerializer(
            data=request.data, partial=True, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            DiscordWebhooks.general_updates(
                WebHookCategory.ROLE.value,
                WebHookActions.CREATE.value,
                request.data.get("title"),
            )

            return CustomResponse(
                response={"data": serializer.data}
            ).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()


class RoleManagementCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Roles'],
        description="Retrieve Role Management C S V.",
        responses={200: dash_roles_serializer.RoleDashboardSerializer},
    )
    def get(self, request):
        role = Role.objects.all()

        role_serializer_data = dash_roles_serializer.RoleDashboardSerializer(
            role, many=True
        ).data
        return CommonUtils.generate_csv(role_serializer_data, "Roles")


class UserRoleSearchAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Roles'],
        description="Retrieve User Role Search.",
        responses={200: dash_roles_serializer.UserRoleSearchSerializer},
    )
    def get(self, request, role_id):
        user = User.objects.filter(user_role_link_user__role_id=role_id).distinct()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            user,
            request,
            ["muid", "full_name"],
            {"muid": "muid", "full_name": "full_name"},
        )

        serialized_data = dash_roles_serializer.UserRoleSearchSerializer(
            paginated_queryset.get("queryset"), many=True
        ).data

        return CustomResponse().paginated_response(
            data=serialized_data,
            pagination=paginated_queryset.get("pagination"),
        )


class UserRoleLinkManagement(APIView):
    authentication_classes = [CustomizePermission]
    """
    This API is creates an interface to help manage the user and role link
    by providing support for
    - Listing all users with the given role (paginated)
    - Giving a lot of users a specific role
    """

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Roles'],
        description="Retrieve User Role Link Management.",
        responses={200: dash_roles_serializer.UserRoleLinkManagementSerializer},
    )
    def get(self, request, role_id):
        """
        Lists all the users with a given role
        """
        users = User.objects.filter(user_role_link_user__role__pk=role_id).distinct()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["muid", "full_name"],
            {"muid": "muid", "full_name": "full_name"},
        )

        serialized_users = dash_roles_serializer.UserRoleLinkManagementSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serialized_users.data,
            pagination=paginated_queryset.get("pagination"),
        )

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Roles'],
        description="Update User Role Link Management.",
        responses={200: dash_roles_serializer.UserRoleLinkManagementSerializer},
    )
    def put(self, request, role_id):
        """
        Lists all the users without a given role;
        used to assign roles
        """
        users = User.objects.filter(
            ~Q(user_role_link_user__role__pk=role_id)
        ).distinct()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["muid", "full_name"],
            {"muid": "muid", "full_name": "full_name"},
        )

        serialized_users = dash_roles_serializer.UserRoleLinkManagementSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serialized_users.data,
            pagination=paginated_queryset.get("pagination"),
        )

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Roles'],
        description=(
            "Assign a role to many users ({users: [user ids]}). Mentor and Company are refused "
            "(use user-role/). Intern and Intern Lead need team_id: each user is handled on their "
            "own (new or removed users join the team, an active intern of that team given Intern "
            "Lead is promoted, anyone else fails) and failures are listed without failing the rest."
        ),
        request=dash_roles_serializer.RoleAssignmentSerializer,
        responses={200: dash_roles_serializer.UserRoleLinkManagementSerializer},
    )
    def post(self, request, role_id):
        """
        Assigns a large bunch of users a certain role.
        Blocked for special roles (Mentor, Company) that require per-user
        provisioning — use POST /dashboard/roles/user-role/ instead.
        Intern / Intern Lead are handled per user with a team (see _assign_members).
        """
        # Guard: block bulk-assign for roles that require individual provisioning
        _SPECIAL_ROLES = [
            RoleType.MENTOR.value,
            RoleType.COMPANY.value,
        ]
        role_obj = Role.objects.filter(pk=role_id).first()
        if role_obj and role_obj.title in MEMBER_ROLES:
            return self._assign_members(request, role_obj)
        if role_obj and role_obj.title in _SPECIAL_ROLES:
            return CustomResponse(
                general_message=(
                    f"The '{role_obj.title}' role cannot be bulk-assigned because it requires "
                    f"additional provisioning. Use POST /dashboard/roles/user-role/ instead."
                )
            ).get_failure_response()

        request_data = request.data.copy()
        request_data["role"] = role_id
        request_data["created_by"] = JWTUtils.fetch_user_id(request)
        serialized_users = dash_roles_serializer.RoleAssignmentSerializer(
            data=request_data
        )
        if serialized_users.is_valid():
            users, role = serialized_users.save()
            return CustomResponse(
                general_message=f"Successfully gave {len(users)} users '{role.title}' role"
            ).get_success_response()
        return CustomResponse(response=serialized_users.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Roles'], description="Partially update User Role Link Management.",
        responses={200: dash_roles_serializer.UserRoleLinkManagementSerializer},
    )
    def patch(self, request, role_id):
        """
        Removes a role from a large bunch of users
        """
        try:
            role = Role.objects.get(pk=role_id)
            user_role_links = UserRoleLink.objects.filter(
                user__pk__in=request.data.get("users"),
                role=role,
            )
            user_ids = list(user_role_links.values_list("user_id", flat=True))
            number = len(user_ids)

            with transaction.atomic():
                user_role_links.delete()
                # Taking Intern away deactivates the membership and removes
                # Intern Lead too; taking Intern Lead away only demotes.
                if role.title == RoleType.INTERN.value:
                    deactivate_members(user_ids, JWTUtils.fetch_user_id(request), role=InternActorRole.ADMIN.value)
                elif role.title == RoleType.INTERN_LEAD.value:
                    record_lead_removed(user_ids, JWTUtils.fetch_user_id(request), role=InternActorRole.ADMIN.value)
            # After the delete, in chunks: the sync used to go out first,
            # so a failed delete still stripped the Discord roles, and past ~53
            # users the single message was too long to reach Discord at all.
            DiscordWebhooks.bulk_role_updates(
                WebHookActions.DELETE.value,
                role.title,
                user_ids,
            )

            return CustomResponse(
                general_message=(
                    f"Successfully removed the '{role.title}' role from {number} users"
                )
            ).get_success_response()
        except Role.DoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    MAX_BULK_MEMBERS = 200

    def _assign_members(self, request, role):
        """Intern / Intern Lead for many users: one transaction per user, failures reported."""
        users = request.data.get("users")
        team_id = request.data.get("team_id")
        # One tenure for everyone in the list; required for people who are added, not promoted.
        join_date = parse_date(request.data.get("join_date"))
        end_date = parse_date(request.data.get("end_date"))
        if not team_id:
            return CustomResponse(
                general_message=f"team_id is required when assigning the '{role.title}' role."
            ).get_failure_response()
        team = InternTeam.objects.filter(id=team_id).first()
        if team is None:
            return CustomResponse(general_message="No team with this id.").get_failure_response()
        if not team.is_active:
            return CustomResponse(
                general_message=f"{team.name} ({team.code}) is inactive. Activate it first."
            ).get_failure_response()
        if not isinstance(users, list) or not users:
            return CustomResponse(general_message="users must be a non-empty list of user ids.").get_failure_response()
        user_ids = list(dict.fromkeys(str(u) for u in users))
        if len(user_ids) > self.MAX_BULK_MEMBERS:
            return CustomResponse(
                general_message=f"At most {self.MAX_BULK_MEMBERS} users per request."
            ).get_failure_response()

        actor_id = JWTUtils.fetch_user_id(request)
        users_by_id = {u.id: u for u in User.objects.filter(id__in=user_ids).only("id", "muid")}
        succeeded, promoted, failed = [], 0, []
        for user_id in user_ids:
            user = users_by_id.get(user_id)
            if user is None:
                failed.append({"user_id": user_id, "muid": None, "reason": "No user with this id."})
                continue
            try:
                with transaction.atomic():
                    outcome = import_intern(
                        user, team, actor_id, make_lead=role.title == RoleType.INTERN_LEAD.value,
                        role=InternActorRole.ADMIN.value, join_date=join_date, end_date=end_date,
                    )
                succeeded.append(user.id)
                promoted += outcome == "promoted"
            except OnboardError as e:
                failed.append({"user_id": user.id, "muid": user.muid, "reason": str(e)})

        if succeeded:
            DiscordWebhooks.bulk_role_updates(WebHookActions.UPDATE.value, role.title, succeeded)

        return CustomResponse(
            general_message=f"Gave {len(succeeded)} of {len(user_ids)} users the '{role.title}' role in {team.name}",
            response={
                "success_count": len(succeeded),
                "promoted_count": promoted,
                "failed_count": len(failed),
                "failed": failed,
            },
        ).get_success_response()


class UserRole(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Roles'],
        description="Create User Role.",
        request=dash_roles_serializer.UserRoleCreateSerializer,
        responses={200: dash_roles_serializer.UserRoleCreateSerializer},
    )
    def post(self, request):
        serializer = dash_roles_serializer.UserRoleCreateSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        try:
            role_link = serializer.save()
        except OnboardError as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

        DiscordWebhooks.general_updates(
            WebHookCategory.USER_ROLE.value,
            WebHookActions.UPDATE.value,
            request.data.get("user_id"),
        )

        response_data = {"message": "Role Added Successfully"}
        # If this was a Mentor role assignment, tell the admin whether
        # the UserMentor profile was freshly created or already existed.
        if hasattr(role_link, '_mentor_profile_created'):
            response_data["mentor_profile_created"] = role_link._mentor_profile_created
        # Intern / Intern Lead: whether the user joined a team (new or brought back)
        # or was promoted in their team, and which team.
        if hasattr(role_link, '_intern_team_created'):
            response_data["intern_team_created"] = role_link._intern_team_created
            response_data["promoted"] = role_link._intern_promoted
            response_data["team"] = role_link._intern_team
        # If this was a Company role assignment, tell the admin whether
        # the Company profile was freshly created or an existing record was verified.
        if hasattr(role_link, '_company_created'):
            response_data["company_created"] = role_link._company_created

        return CustomResponse(
            general_message="Role Added Successfully",
            response=response_data,
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Roles'], description="Delete User Role.",
        responses={200: dash_roles_serializer.UserRoleCreateSerializer},
    )
    def delete(self, request):
        user_id_str = request.data.get("user_id")
        role_id     = request.data.get("role_id")

        try:
            user_role_link = UserRoleLink.objects.select_related("role", "user").get(
                role_id=role_id, user_id=user_id_str
            )
        except UserRoleLink.DoesNotExist:
            return CustomResponse(
                general_message="Role link not found."
            ).get_failure_response()

        role_title = user_role_link.role.title
        user       = user_role_link.user
        admin_id   = JWTUtils.fetch_user_id(request)
        now        = DateTimeUtils.get_current_utc_time()

        with transaction.atomic():
            user_role_link.delete()

            # ── Mentor cleanup ──────────────────────────────────────────────
            if role_title == RoleType.MENTOR.value:
                from db.user import MentorApplication, MentorScopeGrant

                applications = MentorApplication.objects.filter(
                    user=user, status=MentorApplication.Status.APPROVED
                )
                for app in applications:
                    app.status = MentorApplication.Status.REJECTED
                    app.updated_by_id = admin_id
                    app.updated_at = now
                    app.save(update_fields=["status", "updated_by_id", "updated_at"])

                    if app.mentor_tier == MentorApplication.MentorTier.IG_MENTOR and app.preferred_ig_ids:
                        # Only release IGs no OTHER still-APPROVED application
                        # (e.g. a separate COMPANY_MENTOR app listing the same
                        # IG) still relies on.
                        from api.dashboard.mentor.dash_mentor_helper import release_mentor_ig_links
                        release_mentor_ig_links(
                            user, app.preferred_ig_ids,
                            exclude_application_id=app.id, actor_user_id=admin_id,
                        )

                    MentorScopeGrant.objects.filter(
                        application=app, is_active=True
                    ).update(
                        is_active=False,
                        revoked_by_id=admin_id,
                        revoked_at=now,
                    )

            # ── Intern cleanup ──────────────────────────────────────────────
            # Same as deactivating the intern: membership ended and Intern Lead
            # removed too. Removing Intern Lead alone only demotes (recorded in history).
            elif role_title == RoleType.INTERN.value:
                deactivate_members([user.id], admin_id, role=InternActorRole.ADMIN.value)
            elif role_title == RoleType.INTERN_LEAD.value:
                record_lead_removed([user.id], admin_id, role=InternActorRole.ADMIN.value)

            # ── Company cleanup ──────────────────────────────────────────────
            elif role_title == RoleType.COMPANY.value:
                from db.company import Company
                from api.dashboard.company.company_views import _deactivate_company
                # Reuse the same deactivation path as the dedicated company
                # deactivation endpoints (PRD §4.2/§4.3) rather than a separate
                # ad hoc "suspended" status, so admin-link revocation, status
                # gating, and admin summary counts all stay consistent
                # regardless of which surface triggered it.
                company = Company.objects.filter(company_user_id=user.id, status="verified").first()
                if company:
                    _deactivate_company(company, admin_id)

        DiscordWebhooks.general_updates(
            WebHookCategory.USER_ROLE.value,
            WebHookActions.DELETE.value,
            user_role_link.id,
        )
        return CustomResponse(
            general_message="User Role deleted successfully"
        ).get_success_response()


class RoleBaseTemplateAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Roles'], description=(
        "Download the role bulk-assign template: columns muid, role and team (an intern team "
        "code, needed on Intern / Intern Lead rows). 'Data Definitions' lists roles and team codes."
    ),
        responses={200: OpenApiResponse(description="XLSX file download")},
    )
    def get(self, request):
        wb = load_workbook("./excel-templates/role_base_template.xlsx")
        # Optional third column: team code, required on Intern / Intern Lead rows.
        # Optional columns: team code, join_date, end_date (YYYY-MM-DD), needed on rows
        # that add a new intern (Intern / Intern Lead).
        wb.worksheets[0].cell(row=1, column=3, value="team")
        wb.worksheets[0].cell(row=1, column=4, value="join_date")
        wb.worksheets[0].cell(row=1, column=5, value="end_date")
        ws = wb["Data Definitions"]

        roles = Role.objects.all().values_list("title", flat=True)
        team_codes = InternTeam.objects.filter(is_active=True).order_by("code").values_list("code", flat=True)
        data = {"role": roles, "team": team_codes}
        # Write data column-wise
        for col_num, (col_name, col_values) in enumerate(data.items(), start=1):
            ws.cell(row=1, column=col_num, value=col_name)
            for row, value in enumerate(col_values, start=2):
                ws.cell(row=row, column=col_num, value=value)

        # Save the file
        with NamedTemporaryFile() as tmp:
            tmp.close()  # with statement opened tmp, close it so wb.save can open it
            wb.save(tmp.name)
            with open(tmp.name, "rb") as f:
                f.seek(0)
                new_file_object = f.read()
        return FileResponse(
            BytesIO(new_file_object),
            as_attachment=True,
            filename="role_base_template.xlsx",
        )


class UserRoleBulkAssignAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Roles'],
        description="Create User Role Bulk Assign.",
        request=dash_roles_serializer.UserRoleBulkAssignSerializer,
        responses={200: dash_roles_serializer.UserRoleBulkAssignSerializer},
    )
    def post(self, request):
        try:
            file_obj = request.FILES["user_roles_list"]
        except KeyError:
            return CustomResponse(
                general_message="File not found."
            ).get_failure_response()

        excel_data = ImportCSV()
        excel_data = excel_data.read_excel_file(file_obj)

        if not excel_data:
            return CustomResponse(
                general_message="Empty csv file."
            ).get_failure_response()

        temp_headers = ["muid", "role"]
        first_entry = excel_data[0]
        for key in temp_headers:
            if key not in first_entry:
                return CustomResponse(
                    general_message=f"{key} does not exist in the file."
                ).get_failure_response()

        excel_data = [row for row in excel_data if any(row.values())]
        valid_rows = []
        error_rows = []
        success_data = []
        users_to_fetch = set()
        roles_to_fetch = set()
        user_role_link_to_check = set()

        for row in excel_data[1:]:
            keys_to_keep = ["muid", "role", "team", "join_date", "end_date"]
            row_keys = list(row.keys())
            # Remove columns other than "muid" and "role"
            for key in row_keys:
                if key not in keys_to_keep:
                    del row[key]

        for row in excel_data[1:]:
            user = row.get("muid")
            role = row.get("role")
            users_to_fetch.add(user)
            roles_to_fetch.add(role)
            if (user, role) in user_role_link_to_check:
                row["error"] = "Duplicate entry"
                error_rows.append(row)
                excel_data.remove(row)
            else:
                user_role_link_to_check.add((user, role))

        users = User.objects.filter(muid__in=users_to_fetch).values(
            "id",
            "muid",
        )
        roles = Role.objects.filter(title__in=roles_to_fetch).values(
            "id",
            "title",
        )
        existing_user_role_links = list(
            UserRoleLink.objects.filter(
                user__muid__in=users_to_fetch, role__title__in=roles_to_fetch
            ).values_list("user__muid", "role__title")
        )
        users_dict = {user["muid"]: user["id"] for user in users}
        roles_dict = {role["title"]: role["id"] for role in roles}
        users_by_role = {role_title: [] for role_title in roles_dict.keys()}
        teams_by_code = {team.code.upper(): team for team in InternTeam.objects.filter(is_active=True)}
        member_rows_done = {}  # role title -> user ids given that role through a team
        request_user_id = JWTUtils.fetch_user_id(request)

        for row in excel_data[1:]:
            user = row.pop("muid")
            role = row.pop("role")
            team_code = str(row.pop("team", None) or "").strip()
            join_date = parse_date(row.pop("join_date", None))
            end_date = parse_date(row.pop("end_date", None))

            user_id = users_dict.get(user)
            role_id = roles_dict.get(role)
            if not user_id:
                row["muid"] = user
                row["role"] = role
                row["error"] = f"Invalid user muid: {user}"
                error_rows.append(row)
            elif not role_id:
                row["muid"] = user
                row["role"] = role
                row["error"] = f"Invalid role: {role}"
                error_rows.append(row)
            elif role in MEMBER_ROLES:
                # Intern / Intern Lead: membership and roles together, per row,
                # with the same rules as the intern import.
                error = None
                team = teams_by_code.get(team_code.upper())
                if not team_code:
                    error = "team is required for the Intern and Intern Lead roles."
                elif team is None:
                    error = f"No team with code '{team_code}'."
                else:
                    try:
                        with transaction.atomic():
                            import_intern(
                                User(id=user_id, muid=user), team, request_user_id,
                                make_lead=role == RoleType.INTERN_LEAD.value, role=InternActorRole.ADMIN.value,
                                join_date=join_date, end_date=end_date,
                            )
                        success_data.append({"user": user_id, "role": role_id})
                        member_rows_done.setdefault(role, []).append(user_id)
                    except OnboardError as e:
                        error = str(e)
                if error:
                    row.update({"muid": user, "role": role, "team": team_code, "error": error})
                    error_rows.append(row)
            elif (user, role) in existing_user_role_links:
                row["muid"] = user
                row["role"] = role
                row["error"] = f"User {user} already has role {role}"
                error_rows.append(row)
            else:
                users_by_role[role].append(user_id)
                row["id"] = str(uuid.uuid4())
                row["user_id"] = user_id
                row["role_id"] = role_id
                row["verified"] = True
                row["created_by_id"] = request_user_id
                valid_rows.append(row)

        users_by_role = {
            role_title: users for role_title, users in users_by_role.items() if users
        }
        for role, user_set in member_rows_done.items():
            DiscordWebhooks.bulk_role_updates(WebHookActions.UPDATE.value, role, user_set)

        user_roles_serializer = dash_roles_serializer.UserRoleBulkAssignSerializer(
            data=valid_rows, many=True
        )
        if user_roles_serializer.is_valid():
            user_roles_serializer.save()
            for user_role_data in user_roles_serializer.data:
                success_data.append(
                    {
                        "user": user_role_data.get("user_id", ""),
                        "role": user_role_data.get("role_id", ""),
                    }
                )
            for role, user_set in users_by_role.items():
                DiscordWebhooks.bulk_role_updates(
                    WebHookActions.UPDATE.value,
                    role,
                    user_set,
                )
        else:
            error_rows.append(user_roles_serializer.errors)

        return CustomResponse(
            response={"Success": success_data, "Failed": error_rows}
        ).get_success_response()
