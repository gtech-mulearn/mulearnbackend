import uuid
from datetime import timedelta

from django.db.models import Count, F, Q, Sum
from rest_framework.views import APIView

from db.campus import CampusExecom, CampusExecomRole, CampusIGChapter, CampusSocialLink
from db.organization import Organization, UserOrganizationLink
from db.task import Level, Wallet, InterestGroup, KarmaActivityLog
from db.user import User, Role, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils, DateTimeUtils
from . import serializers
from .dash_campus_helper import (
    get_user_college_link,
    validate_campus_member,
    get_campus_ig_chapter,
    assign_ig_lead_role,
)


class CampusDetailsPublicAPI(APIView):
    """
    Campus Details API

    This API view allows authorized users with specific roles (Campus Lead or Enabler)
    to access details about their campus

    Attributes:
        authentication_classes (list): A list containing the CustomizePermission class for authentication.

    Method:
        get(request): Handles GET requests to retrieve campus details for the authenticated user.
    """

    authentication_classes = [CustomizePermission]

    # Use the role_required decorator to specify the allowed roles for this view
    # @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request, org_id):

        if not org_id:
            return CustomResponse(
                general_message="College not found"
            ).get_failure_response()

        org = Organization.objects.filter(
            id=org_id, org_type=OrganizationType.COLLEGE.value
        ).first()

        if org is None:
            return CustomResponse(
                general_message="College not found"
            ).get_failure_response()

        serializer = serializers.CampusDetailsPublicSerializer(org, many=False)

        return CustomResponse(response=serializer.data).get_success_response()


class CampusDetailsAPI(APIView):
    """
    Campus Details API

    This API view allows authorized users with specific roles (Campus Lead or Enabler)
    to access details about their campus

    Attributes:
        authentication_classes (list): A list containing the CustomizePermission class for authentication.

    Method:
        get(request): Handles GET requests to retrieve campus details for the authenticated user.
    """

    authentication_classes = [CustomizePermission]

    # Use the role_required decorator to specify the allowed roles for this view
    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        # Fetch the user's ID from the request using JWTUtils
        user_id = JWTUtils.fetch_user_id(request)

        # Get the user's organization link using the user ID
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        # Check if the user's organization link is None
        if user_org_link.org is None:
            # If it is None, return a failure response with a specific message
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        # # Serialize the user's organization link using the CampusDetailsSerializer
        serializer = serializers.CampusDetailsSerializer(user_org_link, many=False)

        # Return a success response with the serialized data
        return CustomResponse(response=serializer.data).get_success_response()


class CampusStudentInEachLevelAPI(APIView):
    authentication_classes = [CustomizePermission]

    # @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request, org_id=None):
        if org_id:
            org = Organization.objects.filter(
                id=org_id, org_type=OrganizationType.COLLEGE.value
            ).first()
            if not org:
                return CustomResponse(
                    general_message="College not found"
                ).get_failure_response()
        else:
            user_id = JWTUtils.fetch_user_id(request)

            if not (user_org_link := get_user_college_link(user_id)):
                return CustomResponse(
                    general_message="User have no organization"
                ).get_failure_response()

            if user_org_link.org is None:
                return CustomResponse(
                    general_message="Campus lead has no college"
                ).get_failure_response()
            org = user_org_link.org

        level_with_student_count = Level.objects.annotate(
            students=Count(
                "user_lvl_link_level__user",
                filter=Q(
                    user_lvl_link_level__user__user_organization_link_user__org=org
                ),
            )
        ).values(level=F("level_order"), students=F("students"))

        return CustomResponse(response=level_with_student_count).get_success_response()


class CampusStudentDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()
        is_alumni = request.query_params.get("is_alumni")

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()
        if is_alumni:
            rank = (
                Wallet.objects.filter(
                    user__user_organization_link_user__org=user_org_link.org,
                    user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                    user__user_organization_link_user__is_alumni=is_alumni,
                )
                .distinct()
                .order_by("-karma", "-created_at")
                .values(
                    "user_id",
                    "karma",
                )
            )

            ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

            user_org_links = (
                User.objects.filter(
                    user_organization_link_user__org=user_org_link.org,
                    user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                    user_organization_link_user__is_alumni=is_alumni,
                )
                .distinct()
                .annotate(
                    user_id=F("id"),
                    email_=F("email"),
                    mobile_=F("mobile"),
                    karma=F("wallet_user__karma"),
                    level=F("user_lvl_link_user__level__name"),
                    join_date=F("created_at"),
                    last_karma_gained=F("wallet_user__karma_last_updated_at"),
                    department=F("user_organization_link_user__department__title"),
                    graduation_year=F("user_organization_link_user__graduation_year"),
                    is_alumni=F("user_organization_link_user__is_alumni"),
                )
            )
        else:
            rank = (
                Wallet.objects.filter(
                    user__user_organization_link_user__org=user_org_link.org,
                    user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                )
                .distinct()
                .order_by("-karma", "-created_at")
                .values(
                    "user_id",
                    "karma",
                )
            )

            ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

            user_org_links = (
                User.objects.filter(
                    user_organization_link_user__org=user_org_link.org,
                    user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                )
                .distinct()
                .annotate(
                    user_id=F("id"),
                    email_=F("email"),
                    mobile_=F("mobile"),
                    karma=F("wallet_user__karma"),
                    level=F("user_lvl_link_user__level__name"),
                    join_date=F("created_at"),
                    last_karma_gained=F("wallet_user__karma_last_updated_at"),
                    department=F("user_organization_link_user__department__title"),
                    graduation_year=F("user_organization_link_user__graduation_year"),
                    is_alumni=F("user_organization_link_user__is_alumni"),
                )
            )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            user_org_links,
            request,
            ["full_name", "level"],
            {
                "full_name": "full_name",
                "muid": "muid",
                "karma": "wallet_user__karma",
                "level": "user_lvl_link_user__level__level_order",
                # "is_active": "karma_activity_log_user__created_at",
                "join_date": "created_at",
                "email": "email_",
                "mobile": "mobile_",
                "is_alumni": "is_alumni",
            },
        )

        serializer = serializers.CampusStudentDetailsSerializer(
            paginated_queryset.get("queryset"), many=True, context={"ranks": ranks}
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class CampusStudentDetailsCSVAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()
        is_alumni = request.query_params.get("is_alumni")

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        if is_alumni:
            rank = (
                Wallet.objects.filter(
                    user__user_organization_link_user__org=user_org_link.org,
                    user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                    user__user_organization_link_user__is_alumni=is_alumni,
                )
                .distinct()
                .order_by("-karma", "-created_at")
                .values(
                    "user_id",
                    "karma",
                )
            )

            ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

            user_org_links = (
                User.objects.filter(
                    user_organization_link_user__org=user_org_link.org,
                    user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                    user_organization_link_user__is_alumni=is_alumni,
                )
                .distinct()
                .annotate(
                    user_id=F("id"),
                    email_=F("email"),
                    mobile_=F("mobile"),
                    karma=F("wallet_user__karma"),
                    level=F("user_lvl_link_user__level__name"),
                    join_date=F("created_at"),
                    last_karma_gained=F("wallet_user__karma_last_updated_at"),
                    department=F("user_organization_link_user__department__title"),
                    graduation_year=F("user_organization_link_user__graduation_year"),
                    is_alumni=F("user_organization_link_user__is_alumni"),
                )
            )
        else:
            rank = (
                Wallet.objects.filter(
                    user__user_organization_link_user__org=user_org_link.org,
                    user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                )
                .distinct()
                .order_by("-karma", "-created_at")
                .values(
                    "user_id",
                    "karma",
                )
            )

            ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

            user_org_links = (
                User.objects.filter(
                    user_organization_link_user__org=user_org_link.org,
                    user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                )
                .distinct()
                .annotate(
                    user_id=F("id"),
                    email_=F("email"),
                    mobile_=F("mobile"),
                    karma=F("wallet_user__karma"),
                    level=F("user_lvl_link_user__level__name"),
                    join_date=F("created_at"),
                    last_karma_gained=F("wallet_user__karma_last_updated_at"),
                    department=F("user_organization_link_user__department__title"),
                    graduation_year=F("user_organization_link_user__graduation_year"),
                    is_alumni=F("user_organization_link_user__is_alumni"),
                )
            )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            user_org_links,
            request,
            ["full_name", "level"],
            {
                "full_name": "full_name",
                "muid": "muid",
                "karma": "wallet_user__karma",
                "level": "user_lvl_link_user__level__level_order",
                # "is_active": "karma_activity_log_user__created_at",
                "join_date": "created_at",
                "email": "email_",
                "mobile": "mobile_",
                "is_alumni": "is_alumni",
            },
        )

        serializer = serializers.CampusStudentDetailsSerializer(
            user_org_links, many=True, context={"ranks": ranks}
        )
        return CommonUtils.generate_csv(serializer.data, "Campus Student Details")


class WeeklyKarmaAPI(APIView):
    authentication_classes = [CustomizePermission]

    # @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request, org_id=None):
        if org_id:
            org = Organization.objects.filter(
                id=org_id, org_type=OrganizationType.COLLEGE.value
            ).first()
            if not org:
                return CustomResponse(
                    general_message="College not found"
                ).get_failure_response()
        else:
            user_id = JWTUtils.fetch_user_id(request)

            if not (user_org_link := get_user_college_link(user_id)):
                return CustomResponse(
                    general_message="User have no organization"
                ).get_failure_response()

            if user_org_link.org is None:
                return CustomResponse(
                    general_message="Campus lead has no college"
                ).get_failure_response()
            org = user_org_link.org

        serializer = serializers.WeeklyKarmaSerializer(org, many=False)
        return CustomResponse(response=serializer.data).get_success_response()


class ChangeStudentTypeAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def patch(self, request, member_id):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()
        user_org_link_obj = UserOrganizationLink.objects.filter(
            user__id=member_id,
            org=user_org_link.org,
            org__org_type=OrganizationType.COLLEGE.value,
        ).first()

        serializer = serializers.ChangeStudentTypeSerializer(
            user_org_link_obj, data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Student Type updated successfully"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class TransferLeadRoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        new_lead_muid = request.data.get("new_lead_muid", None)
        if new_lead_muid is None:
            return CustomResponse(
                general_message="Required data is missing"
            ).get_failure_response()

        new_lead = User.objects.filter(muid=new_lead_muid).first()
        if new_lead is None:
            return CustomResponse(
                general_message="Can't find the user"
            ).get_failure_response()

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()
        validate_new_lead = UserOrganizationLink.objects.filter(
            user__id=new_lead.id,
            org=user_org_link.org,
            org__org_type=OrganizationType.COLLEGE.value,
            is_alumni=False,
        ).first()
        if validate_new_lead is None:
            return CustomResponse(
                general_message="Can't find the user in your college"
            ).get_failure_response()

        role_id = Role.objects.filter(title=RoleType.CAMPUS_LEAD.value).first()
        if role_id is None:
            return CustomResponse(
                general_message="Can't find the role"
            ).get_failure_response()
        role_id = role_id.id

        UserRoleLink.objects.filter(
            user__id=user_id,
            role__id=role_id,
        ).delete()

        serializer = serializers.UserRoleLinkSerializer(
            data={
                "user": new_lead.id,
                "role": role_id,
            },
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Assigned new Campus Lead successfully"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class TransferEnablerRoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        new_enabler_muid = request.data.get("new_enabler_muid", None)
        if new_enabler_muid is None:
            return CustomResponse(
                general_message="Required data is missing"
            ).get_failure_response()

        new_enabler = User.objects.filter(muid=new_enabler_muid).first()
        if new_enabler is None:
            return CustomResponse(
                general_message="Can't find the user"
            ).get_failure_response()

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()
        validate_new_enabler = UserOrganizationLink.objects.filter(
            user__id=new_enabler.id,
            org=user_org_link.org,
            org__org_type=OrganizationType.COLLEGE.value,
            is_alumni=False,
        ).first()

        if validate_new_enabler is None:
            return CustomResponse(
                general_message="Can't find the user in your college"
            ).get_failure_response()

        role_id = Role.objects.filter(title=RoleType.LEAD_ENABLER.value).first()
        if role_id is None:
            return CustomResponse(
                general_message="Can't find the role"
            ).get_failure_response()
        role_id = role_id.id

        current_enabler = UserRoleLink.objects.filter(
            user__user_organization_link_user__org=user_org_link.org,
            user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            role__id=role_id,
        ).first()
        if current_enabler:
            current_enabler.delete()

        serializer = serializers.UserRoleLinkSerializer(
            data={
                "user": new_enabler.id,
                "role": role_id,
            },
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Assigned new Enabler Lead successfully"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class TransferIGRoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()
        ig_list = (
            User.objects.filter(
                user_organization_link_user__org=user_org_link.org,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .values_list("user_ig_link_user__ig__code", flat=True)
            .distinct()
        )

        return CustomResponse(response={"ig_list": ig_list}).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        new_ig_muid = request.data.get("new_ig_muid", None)
        ig_code = request.data.get("ig_code", None)

        if new_ig_muid is None or ig_code is None:
            return CustomResponse(
                general_message="Required data is missing"
            ).get_failure_response()

        new_ig = User.objects.filter(muid=new_ig_muid).first()
        if new_ig is None:
            return CustomResponse(
                general_message="Can't find the user"
            ).get_failure_response()

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()
        validate_ig = UserOrganizationLink.objects.filter(
            user__id=new_ig.id,
            org=user_org_link.org,
            org__org_type=OrganizationType.COLLEGE.value,
            is_alumni=False,
        ).first()
        if validate_ig is None:
            return CustomResponse(
                general_message="Can't find the user in your college"
            ).get_failure_response()

        # need to change title according to the ig role
        # below code filter role for title=ig_code+CampusLead
        role_id = Role.objects.filter(title=f"{ig_code}CampusLead").first()
        if role_id is None:
            return CustomResponse(
                general_message="Can't find the role"
            ).get_failure_response()
        role_id = role_id.id

        current_ig = UserRoleLink.objects.filter(
            user__user_organization_link_user__org=user_org_link.org,
            user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            role__id=role_id,
        ).first()
        if current_ig:
            current_ig.delete()

        serializer = serializers.UserRoleLinkSerializer(
            data={
                "user": new_ig.id,
                "role": role_id,
            },
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Assigned new Ig lead successfully"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


# ── New views for campus dashboard ────────────────────────────────


class CampusLeaderboardAPI(APIView):
    """GET leaderboard/ — paginated, filterable, ranked student list."""
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org

        # Base queryset: all students in campus
        qs = User.objects.filter(
            user_organization_link_user__org=org,
            user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
        ).distinct()

        # Optional filters
        pass_out_year = request.query_params.get("pass_out_year")
        if pass_out_year:
            qs = qs.filter(user_organization_link_user__graduation_year=pass_out_year)

        ig_id = request.query_params.get("ig_id")
        if ig_id:
            qs = qs.filter(user_ig_link_user__ig_id=ig_id)

        cluster = request.query_params.get("cluster")
        if cluster:
            qs = qs.filter(user_ig_link_user__ig__cluster=cluster)

        is_alumni = request.query_params.get("is_alumni")
        if is_alumni is not None:
            qs = qs.filter(
                user_organization_link_user__is_alumni=(is_alumni.lower() == "true")
            )

        # Compute global rank dict BEFORE pagination
        rank_qs = (
            Wallet.objects.filter(
                user__user_organization_link_user__org=org,
            )
            .distinct()
            .order_by("-karma", "created_at")
            .values("user_id")
        )
        ranks = {r["user_id"]: i + 1 for i, r in enumerate(rank_qs)}

        # Annotate
        qs = qs.annotate(
            user_id=F("id"),
            karma=F("wallet_user__karma"),
            level=F("user_lvl_link_user__level__name"),
            join_date=F("created_at"),
            last_karma_at=F("wallet_user__karma_last_updated_at"),
            graduation_year=F("user_organization_link_user__graduation_year"),
            department=F("user_organization_link_user__department__title"),
            is_alumni=F("user_organization_link_user__is_alumni"),
            ig_count=Count("user_ig_link_user", distinct=True),
        )

        paginated = CommonUtils.get_paginated_queryset(
            qs,
            request,
            ["full_name", "muid"],
            {
                "karma": "wallet_user__karma",
                "full_name": "full_name",
                "join_date": "created_at",
            },
        )

        serializer = serializers.CampusLeaderboardSerializer(
            paginated.get("queryset"), many=True, context={"ranks": ranks}
        )

        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated.get("pagination"),
            }
        ).get_success_response()


class CampusKarmaByClusterAPI(APIView):
    """GET karma-by-cluster/ — karma totals grouped by IG cluster."""
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org

        result = (
            User.objects.filter(
                user_organization_link_user__org=org,
                user_ig_link_user__isnull=False,
            )
            .values("user_ig_link_user__ig__cluster")
            .annotate(
                total_karma=Sum("wallet_user__karma"),
                member_count=Count("id", distinct=True),
            )
        )

        # Group null cluster as 'unclustered'
        response_data = {}
        for row in result:
            cluster_name = row["user_ig_link_user__ig__cluster"] or "unclustered"
            response_data[cluster_name] = {
                "total_karma": row["total_karma"] or 0,
                "member_count": row["member_count"],
            }

        return CustomResponse(response=response_data).get_success_response()


class CampusEventsAPI(APIView):
    """GET events/ — campus events feed, paginated."""
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        from db.event import Event, EventScope

        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org

        # Campus + campus-IG scoped events
        qs = Event.objects.filter(
            deleted_at__isnull=True,
        ).filter(
            Q(event_scope__scope="campus", event_scope__target_org_id=org.id)
            | Q(event_scope__scope="campus_ig", event_scope__target_ci_org_id=org.id)
        ).select_related(
            "event_scope", "organiser", "venue",
            "organiser__ig_id", "organiser__org_id", "organiser__ci_org_id",
        ).prefetch_related("tag_links__tag").distinct()

        # Optional filters
        status = request.query_params.get("status")
        if status:
            statuses = [s.strip() for s in status.split(",")]
            qs = qs.filter(status__in=statuses)
        else:
            qs = qs.filter(status__in=[Event.Status.PUBLISHED, Event.Status.ONGOING])

        event_type = request.query_params.get("event_type")
        if event_type:
            qs = qs.filter(event_type=event_type)

        scope_filter = request.query_params.get("scope")
        if scope_filter in ("campus", "campus_ig"):
            qs = qs.filter(event_scope__scope=scope_filter)

        start_date = request.query_params.get("start_date")
        if start_date:
            qs = qs.filter(start_datetime__date__gte=start_date)

        end_date = request.query_params.get("end_date")
        if end_date:
            qs = qs.filter(start_datetime__date__lte=end_date)

        paginated = CommonUtils.get_paginated_queryset(
            qs,
            request,
            ["title"],
            {
                "start_datetime": "start_datetime",
                "interest_count": "interest_count",
            },
        )

        serializer = serializers.CampusEventListSerializer(
            paginated.get("queryset"), many=True
        )

        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated.get("pagination"),
            }
        ).get_success_response()


class CampusEventDistributionAPI(APIView):
    """GET events/distribution/ — event count grouped by tag."""
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        from db.event import EventTagLink

        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org

        qs = (
            EventTagLink.objects.filter(event__deleted_at__isnull=True)
            .filter(
                Q(
                    event__event_scope__scope="campus",
                    event__event_scope__target_org_id=org.id,
                )
                | Q(
                    event__event_scope__scope="campus_ig",
                    event__event_scope__target_ci_org_id=org.id,
                )
            )
            .values(tag=F("tag__name"))
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        return CustomResponse(response={"data": list(qs)}).get_success_response()


class CampusExecomAPI(APIView):
    """GET/POST execom/, DELETE execom/<member_id>/"""
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org

        # Fetch all execom assignments for this campus
        execom = CampusExecom.objects.select_related(
            "user", "role"
        ).filter(
            org=org
        ).order_by("role__priority", "role__title")

        serializer = serializers.ExecomMemberSerializer(execom, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org

        input_serializer = serializers.ExecomAddSerializer(data=request.data)
        if not input_serializer.is_valid():
            return CustomResponse(
                message=input_serializer.errors
            ).get_failure_response()

        user_muid = input_serializer.validated_data["user_muid"]
        role_id = input_serializer.validated_data["role_id"]

        # Find the user
        target_user = User.objects.filter(muid=user_muid).first()
        if target_user is None:
            return CustomResponse(
                general_message="Can't find the user"
            ).get_failure_response()

        # Validate campus membership
        if not validate_campus_member(target_user.id, org):
            return CustomResponse(
                general_message="User is not a member of this campus"
            ).get_failure_response()

        # Validate the execom role exists and is active
        execom_role = CampusExecomRole.objects.filter(
            id=role_id, is_active=True
        ).first()
        if execom_role is None:
            return CustomResponse(
                general_message="Invalid or inactive execom role"
            ).get_failure_response()

        # Check not already assigned
        if CampusExecom.objects.filter(
            org=org, user=target_user, role=execom_role
        ).exists():
            return CustomResponse(
                general_message="User already has this execom role in this campus"
            ).get_failure_response()

        # Create the assignment
        CampusExecom.objects.create(
            id=str(uuid.uuid4()),
            org=org,
            user=target_user,
            role=execom_role,
            created_by_id=user_id,
            created_at=DateTimeUtils.get_current_utc_time(),
        )

        return CustomResponse(
            general_message="Execom member added successfully"
        ).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value])
    def delete(self, request, member_id=None):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        org = user_org_link.org

        # member_id is campus_execom.id
        assignment = CampusExecom.objects.select_related(
            "user", "role"
        ).filter(
            id=member_id,
            org=org,
        ).first()

        if assignment is None:
            return CustomResponse(
                general_message="Execom member not found"
            ).get_failure_response()

        assignment.delete()

        return CustomResponse(
            general_message="Execom member removed successfully"
        ).get_success_response()


class CampusIGChapterAPI(APIView):
    """GET/POST ig-chapters/, PATCH/DELETE ig-chapters/<chapter_id>/"""
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org

        chapters = (
            CampusIGChapter.objects.select_related("ig", "lead_user")
            .filter(org=org)
            .annotate(
                member_count=Count(
                    "ig__user_ig_link_ig__user",
                    filter=Q(
                        ig__user_ig_link_ig__user__user_organization_link_user__org=org
                    ),
                    distinct=True,
                )
            )
        )

        serializer = serializers.CampusIGChapterSerializer(chapters, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org

        input_serializer = serializers.CampusIGChapterWriteSerializer(
            data=request.data
        )
        if not input_serializer.is_valid():
            return CustomResponse(
                message=input_serializer.errors
            ).get_failure_response()

        ig_id = input_serializer.validated_data.get("ig_id")
        lead_user_muid = input_serializer.validated_data.get("lead_user_muid")

        # Validate IG exists
        ig = InterestGroup.objects.filter(id=ig_id).first()
        if ig is None:
            return CustomResponse(
                general_message="Interest group not found"
            ).get_failure_response()

        # Check chapter doesn't already exist
        if CampusIGChapter.objects.filter(org=org, ig=ig).exists():
            return CustomResponse(
                general_message="A chapter for this IG already exists"
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()

        # Optionally resolve lead user
        lead_user = None
        if lead_user_muid:
            lead_user = User.objects.filter(muid=lead_user_muid).first()
            if lead_user is None:
                return CustomResponse(
                    general_message="Can't find the lead user"
                ).get_failure_response()
            if not validate_campus_member(lead_user.id, org):
                return CustomResponse(
                    general_message="Lead user is not a member of this campus"
                ).get_failure_response()

        # Create chapter
        chapter = CampusIGChapter.objects.create(
            id=str(uuid.uuid4()),
            org=org,
            ig=ig,
            lead_user=lead_user,
            is_active=True,
            created_by_id=user_id,
            created_at=now,
            updated_by_id=user_id,
            updated_at=now,
        )

        # If lead provided, assign the IG lead role
        if lead_user:
            assign_ig_lead_role(lead_user, ig, org, user_id)

        # Return the new chapter
        serializer = serializers.CampusIGChapterSerializer(chapter)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def patch(self, request, chapter_id=None):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        org = user_org_link.org
        chapter = get_campus_ig_chapter(chapter_id, org)

        if chapter is None:
            return CustomResponse(
                general_message="Chapter not found"
            ).get_failure_response()

        input_serializer = serializers.CampusIGChapterWriteSerializer(
            data=request.data
        )
        if not input_serializer.is_valid():
            return CustomResponse(
                message=input_serializer.errors
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        lead_user_muid = input_serializer.validated_data.get("lead_user_muid")
        is_active = input_serializer.validated_data.get("is_active")

        if lead_user_muid:
            new_lead = User.objects.filter(muid=lead_user_muid).first()
            if new_lead is None:
                return CustomResponse(
                    general_message="Can't find the user"
                ).get_failure_response()
            if not validate_campus_member(new_lead.id, org):
                return CustomResponse(
                    general_message="User is not a member of this campus"
                ).get_failure_response()
            chapter.lead_user = new_lead
            assign_ig_lead_role(new_lead, chapter.ig, org, user_id)

        if is_active is not None:
            chapter.is_active = is_active

        chapter.updated_by_id = user_id
        chapter.updated_at = now
        chapter.save()

        serializer = serializers.CampusIGChapterSerializer(chapter)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value])
    def delete(self, request, chapter_id=None):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        org = user_org_link.org
        chapter = get_campus_ig_chapter(chapter_id, org)

        if chapter is None:
            return CustomResponse(
                general_message="Chapter not found"
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()

        # Remove IG lead role if one is assigned
        if chapter.lead_user:
            role_title = f"{chapter.ig.code}CampusLead"
            UserRoleLink.objects.filter(
                user=chapter.lead_user,
                role__title=role_title,
            ).delete()

        # Soft deactivate
        chapter.is_active = False
        chapter.lead_user = None
        chapter.updated_by_id = user_id
        chapter.updated_at = now
        chapter.save()

        return CustomResponse(
            general_message="Chapter deactivated successfully"
        ).get_success_response()


class CampusSocialLinkAPI(APIView):
    """GET/POST social-links/, DELETE social-links/<link_id>/"""
    authentication_classes = [CustomizePermission]

    def get(self, request):
        """Public — accessible via org_id query param."""
        org_id = request.query_params.get("org_id")

        if not org_id:
            # If no org_id, try authenticated user's org
            user_id = JWTUtils.fetch_user_id(request)
            user_org_link = get_user_college_link(user_id)
            if user_org_link and user_org_link.org:
                org_id = user_org_link.org.id
            else:
                return CustomResponse(
                    general_message="org_id is required"
                ).get_failure_response()

        links = CampusSocialLink.objects.filter(org_id=org_id)
        serializer = serializers.CampusSocialLinkSerializer(links, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def post(self, request):
        """Upsert a social link."""
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org
        platform = request.data.get("platform")
        url = request.data.get("url")
        label = request.data.get("label")

        if not platform or not url:
            return CustomResponse(
                general_message="platform and url are required"
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()

        link, created = CampusSocialLink.objects.update_or_create(
            org=org,
            platform=platform,
            defaults={
                "url": url,
                "label": label,
                "updated_by_id": user_id,
                "updated_at": now,
            },
        )
        if created:
            link.id = str(uuid.uuid4())
            link.created_by_id = user_id
            link.created_at = now
            link.save()

        serializer = serializers.CampusSocialLinkSerializer(link)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def delete(self, request, link_id=None):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        org = user_org_link.org

        link = CampusSocialLink.objects.filter(id=link_id, org=org).first()
        if link is None:
            return CustomResponse(
                general_message="Social link not found"
            ).get_failure_response()

        link.delete()

        return CustomResponse(
            general_message="Social link removed."
        ).get_success_response()
