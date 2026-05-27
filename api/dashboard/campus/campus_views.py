from django.db.models import Count, F,Sum, Subquery, OuterRef
from django.db.models import Q
from django.db import transaction
from rest_framework.views import APIView
from collections import defaultdict
from db.organization import Organization, UserOrganizationLink
from db.task import Level, Wallet, InterestGroup
from db.campus import CampusIGChapter, CampusSocialLink
from db.user import User, Role, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from utils.permissions_drf import RequireCapability
from . import serializers
from .dash_campus_helper import get_user_college_link, get_campus_ig_chapters


class CampusListAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        campuses = Organization.objects.filter(org_type=OrganizationType.COLLEGE.value)
        paginated_queryset = CommonUtils.get_paginated_queryset(
            campuses,
            request,
            ["title", "code"],
            {"title": "title", "code": "code"}
        )
        serializer = serializers.CampusListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


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
    permission_classes = [RequireCapability('campus:dashboard:view')]

    # Use the role_required decorator to specify the allowed roles for this view
    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value, 'CAMPUS_MENTOR'])
    def get(self, request):
        if not hasattr(request, 'auth_context') or not request.auth_context:
            return CustomResponse(general_message="Auth context missing").get_failure_response()
            
        org_id = request.auth_context.org_id
        if not org_id:
            return CustomResponse(general_message="Campus lead has no college").get_failure_response()

        user_id = request.auth_context.user_id
        user_org_link = get_user_college_link(user_id)
        
        if not user_org_link:
            # Mock UserOrganizationLink for Mentors
            org = Organization.objects.filter(id=org_id).first()
            if not org:
                return CustomResponse(general_message="College not found").get_failure_response()
            user_org_link = UserOrganizationLink(user_id=user_id, org=org)

        # # Serialize the user's organization link using the CampusDetailsSerializer
        serializer = serializers.CampusDetailsSerializer(user_org_link, many=False)

        # Return a success response with the serialized data
        return CustomResponse(response=serializer.data).get_success_response()


class CampusStudentInEachLevelAPI(APIView):
    authentication_classes = [CustomizePermission]
    permission_classes = [RequireCapability('campus:analytics:view')]

    # @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value, 'CAMPUS_MENTOR'])
    def get(self, request, org_id=None):
        if org_id:
            if not request.auth_context.is_global and request.auth_context.org_id != org_id:
                return CustomResponse(general_message="You do not have permission to access this organization").get_failure_response()
            org = Organization.objects.filter(
                id=org_id, org_type=OrganizationType.COLLEGE.value
            ).first()
            if not org:
                return CustomResponse(
                    general_message="College not found"
                ).get_failure_response()
        else:
            if not hasattr(request, 'auth_context') or not request.auth_context:
                return CustomResponse(general_message="Auth context missing").get_failure_response()

            org_id = request.auth_context.org_id
            if not org_id:
                return CustomResponse(
                    general_message="Campus lead has no college"
                ).get_failure_response()
                
            org = Organization.objects.filter(
                id=org_id, org_type=OrganizationType.COLLEGE.value
            ).first()

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
    permission_classes = [RequireCapability('campus:students:view')]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value, 'CAMPUS_MENTOR'])
    def get(self, request):
        if not hasattr(request, 'auth_context') or not request.auth_context:
            return CustomResponse(general_message="Auth context missing").get_failure_response()

        org_id = request.auth_context.org_id
        if not org_id:
            return CustomResponse(general_message="Campus lead has no college").get_failure_response()
            
        is_alumni = request.query_params.get("is_alumni")
        is_alumni_filter = None
        if is_alumni is not None:
            is_alumni_filter = str(is_alumni).lower() == "true"

        if is_alumni_filter is not None:
            rank = (
                Wallet.objects.filter(
                    user__user_organization_link_user__org_id=org_id,
                    user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                    user__user_organization_link_user__is_alumni=is_alumni_filter,
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
                    user_organization_link_user__org_id=org_id,
                    user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                    user_organization_link_user__is_alumni=is_alumni_filter,
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
                    user__user_organization_link_user__org_id=org_id,
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
                    user_organization_link_user__org_id=org_id,
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
        is_alumni_filter = None
        if is_alumni is not None:
            is_alumni_filter = str(is_alumni).lower() == "true"

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        if is_alumni_filter is not None:
            rank = (
                Wallet.objects.filter(
                    user__user_organization_link_user__org=user_org_link.org,
                    user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                    user__user_organization_link_user__is_alumni=is_alumni_filter,
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
                    user_organization_link_user__is_alumni=is_alumni_filter,
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

        if user_id == new_lead.id:
            return CustomResponse(
                general_message="User already has this role."
            ).get_failure_response()

        role_id = Role.objects.filter(title=RoleType.CAMPUS_LEAD.value).first()
        if role_id is None:
            return CustomResponse(
                general_message="Can't find the role"
            ).get_failure_response()
        role_id = role_id.id

        if UserRoleLink.objects.filter(user=new_lead, role_id=role_id).exists():
            return CustomResponse(
                general_message="User already has this role."
            ).get_failure_response()

        with transaction.atomic():
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
            
            # This should realistically not happen as validation occurs before, but if it does, 
            # transaction.atomic() handles the rollback safely
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

        if user_id == new_enabler.id:
            return CustomResponse(
                general_message="User already has this role."
            ).get_failure_response()

        role_id = Role.objects.filter(title=RoleType.LEAD_ENABLER.value).first()
        if role_id is None:
            return CustomResponse(
                general_message="Can't find the role"
            ).get_failure_response()
        role_id = role_id.id

        if UserRoleLink.objects.filter(user=new_enabler, role_id=role_id).exists():
            return CustomResponse(
                general_message="User already has this role."
            ).get_failure_response()

        with transaction.atomic():
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

        if user_id == new_ig.id:
            return CustomResponse(
                general_message="User already has this role."
            ).get_failure_response()

        # need to change title according to the ig role
        # below code filter role for title=ig_code + ' CampusLead'
        role_id = Role.objects.filter(title=f"{ig_code} CampusLead").first()
        if role_id is None:
            return CustomResponse(
                general_message="Can't find the role"
            ).get_failure_response()
        role_id = role_id.id

        if UserRoleLink.objects.filter(user=new_ig, role_id=role_id).exists():
            return CustomResponse(
                general_message="User already has this role."
            ).get_failure_response()

        with transaction.atomic():
            UserRoleLink.objects.filter(
                user__user_organization_link_user__org=user_org_link.org,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                role__id=role_id,
            ).delete()

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
                    general_message="Assigned new IG Campus Lead successfully"
                ).get_success_response()
            return CustomResponse(message=serializer.errors).get_failure_response()

# ...existing code...

class CampusStudentLeaderboardAPI(APIView):
    authentication_classes = [CustomizePermission]
    permission_classes = [RequireCapability('campus:students:view')]
    
    def get(self, request, org_id=None):
        if org_id:
            if not request.auth_context.is_global and request.auth_context.org_id != org_id:
                return CustomResponse(general_message="You do not have permission to access this organization").get_failure_response()
            org = Organization.objects.filter(
                id=org_id, org_type=OrganizationType.COLLEGE.value
            ).first()
        else:
            if not hasattr(request, 'auth_context') or not request.auth_context:
                return CustomResponse(general_message="Auth context missing").get_failure_response()
            
            org_id = request.auth_context.org_id
            if not org_id:
                return CustomResponse(general_message="Campus lead has no college").get_failure_response()
                
            org = Organization.objects.filter(
                id=org_id, org_type=OrganizationType.COLLEGE.value
            ).first()
  
        if org is None:
            return CustomResponse(
                general_message="Campus not found"
            ).get_failure_response()
        
       
       
        # 1. Compute Campus rank BEFORE filters/pagination                    #

        rank_qs = (
            Wallet.objects.filter(
                user__user_organization_link_user__org=org,
                user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .order_by("-karma","-created_at")
            .values("user_id")
        )
        ranks = {r["user_id"]: i + 1 for i, r in enumerate(rank_qs)}

     
        # 2. Base queryset - all students with annotations                    #

        qs = (
            User.objects.filter(
                user_organization_link_user__org=org,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .annotate(
                user_id=F("id"),  
                # existing fields from CampusStudentDetailsAPI
                karma=F("wallet_user__karma"),
                level=F("user_lvl_link_user__level__name"),
                join_date=F("created_at"),
             # org join date (fixed from created_at)
                last_karma_gained=F("wallet_user__karma_last_updated_at"),
                department=F("user_organization_link_user__department__title"),
                graduation_year=F("user_organization_link_user__graduation_year"),
                is_alumni=F("user_organization_link_user__is_alumni"),

                # new fields not in existing API
                ig_count=Count(
                    "user_ig_link_user",
                    distinct=True
                ),
            )
            .order_by("-wallet_user__karma", "-wallet_user__created_at")  # ← rank 1 appears on page 1
        )

      
        # 3. Apply optional filters from query params                         #
      
        params = request.query_params

        pass_out_year   = params.get("pass_out_year")
        ig_id           = params.get("ig_id")
        category         = params.get("category")
        is_alumni_param = params.get("is_alumni")
        search          = params.get("search")

        if pass_out_year:
            qs = qs.filter(
                user_organization_link_user__graduation_year=pass_out_year
            )
        if ig_id:
            qs = qs.filter(user_ig_link_user__ig_id=ig_id)

        if category:
            qs = qs.filter(user_ig_link_user__ig__category=category)

        if is_alumni_param is not None and is_alumni_param != "":
            is_alumni_bool = is_alumni_param.lower() == "true"
            qs = qs.filter(
                user_organization_link_user__is_alumni=is_alumni_bool
            )
        if search:
            qs = qs.filter(
                Q(full_name__icontains=search) | Q(muid__icontains=search)
            )

     
        # 4. Paginate using CommonUtils (handles pageIndex, perPage, sortBy)  #
   
        paginated_queryset = CommonUtils.get_paginated_queryset(
            qs,
            request,
            search_fields=["full_name", "muid"],
            sort_fields={
                "full_name":       "full_name",
                "muid":            "muid",
                "karma":           "wallet_user__karma",
                "level":           "user_lvl_link_user__level__level_order",
                "join_date":       "created_at",
                "graduation_year": "user_organization_link_user__graduation_year",
                "is_alumni":       "user_organization_link_user__is_alumni",
            },
        )

        # 5. Serialize and return                                              #
       
        serializer = serializers.CampusLeaderboardSerializer(
            paginated_queryset.get("queryset"),
            many=True,
            context={"ranks": ranks},
        )

        return CustomResponse(
            response={
                "data":       serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class CampusKarmaByClusterAPI(APIView):

    authentication_classes = [CustomizePermission]

    def get(self, request, org_id=None):

        if not org_id:
            return CustomResponse(
                general_message="College not found"
            ).get_failure_response()

        org = Organization.objects.filter(
            id=org_id,
            org_type=OrganizationType.COLLEGE.value
        ).first()

        if org is None:
            return CustomResponse(
                general_message="Campus not found"
            ).get_failure_response()

        # Subquery: fetch each user's karma once — no JOIN fan-out
        wallet_karma_sq = Wallet.objects.filter(
            user=OuterRef("pk")
        ).values("karma")[:1]

        # Single query — LEFT JOIN via isnull=False removed
        # users with NO IG will have category=None → goes to "unclustered"
        all_rows = (
            User.objects.filter(
                user_organization_link_user__org=org,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .annotate(user_karma=Subquery(wallet_karma_sq))
            .values("id", "user_ig_link_user__ig__category", "user_karma")
            .distinct()   # 1 row per (user_id, category) — kills IG fan-out
        )

        # Aggregate in Python
        category_map = defaultdict(lambda: {"total_karma": 0, "member_count": 0, "seen_users": set()})

        for row in all_rows:  # streams from DB — no list() memory spike
            category = row["user_ig_link_user__ig__category"] or "unclustered"
            user_id  = row["id"]
            karma    = row["user_karma"] or 0

            # seen_users guards against edge case where
            # a user has NO IG (category=None) but still appears multiple times
            # due to multiple org links
            if user_id not in category_map[category]["seen_users"]:
                category_map[category]["seen_users"].add(user_id)
                category_map[category]["total_karma"]  += karma
                category_map[category]["member_count"] += 1

        # Build final response — strip seen_users from output
        response = {
            category: {
                "total_karma":  data["total_karma"],
                "member_count": data["member_count"],
            }
            for category, data in category_map.items()
        }

        return CustomResponse(
            response=response
        ).get_success_response()


class CampusIGChapterAPI(APIView):
    authentication_classes = [CustomizePermission]
    permission_classes = [RequireCapability('campus:ig:manage')]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value, 'CAMPUS_MENTOR'])
    def get(self, request):
        if not hasattr(request, 'auth_context') or not request.auth_context:
            return CustomResponse(general_message="Auth context missing").get_failure_response()

        org_id = request.auth_context.org_id
        if not org_id:
            return CustomResponse(general_message="Campus lead has no college").get_failure_response()

        chapters = get_campus_ig_chapters(org_id)
        serializer = serializers.CampusIGChapterListSerializer(chapters, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value, 'CAMPUS_MENTOR'])
    def post(self, request):
        if not hasattr(request, 'auth_context') or not request.auth_context:
            return CustomResponse(general_message="Auth context missing").get_failure_response()
            
        org_id = request.auth_context.org_id
        if not org_id:
            return CustomResponse(general_message="Campus lead has no college").get_failure_response()

        org = Organization.objects.filter(id=org_id).first()
        serializer = serializers.CampusIGChapterCreateSerializer(
            data=request.data,
            context={"user_id": request.auth_context.user_id, "org": org},
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="IG Chapter created successfully"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value, 'CAMPUS_MENTOR'])
    def patch(self, request, chapter_id):
        if not hasattr(request, 'auth_context') or not request.auth_context:
            return CustomResponse(general_message="Auth context missing").get_failure_response()
            
        org_id = request.auth_context.org_id
        if not org_id:
            return CustomResponse(general_message="Campus lead has no college").get_failure_response()

        chapter = CampusIGChapter.objects.filter(
            id=chapter_id,
            org_id=org_id,
        ).first()
        if chapter is None:
            return CustomResponse(
                general_message="IG Chapter not found"
            ).get_failure_response()

        serializer = serializers.CampusIGChapterUpdateSerializer(
            chapter,
            data=request.data,
            partial=True,
            context={"user_id": request.auth_context.user_id},
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="IG Chapter updated successfully"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value, 'CAMPUS_MENTOR'])
    def delete(self, request, chapter_id):
        if not hasattr(request, 'auth_context') or not request.auth_context:
            return CustomResponse(general_message="Auth context missing").get_failure_response()
            
        org_id = request.auth_context.org_id
        if not org_id:
            return CustomResponse(general_message="Campus lead has no college").get_failure_response()

        chapter = CampusIGChapter.objects.filter(
            id=chapter_id,
            org_id=org_id,
        ).first()
        if chapter is None:
            return CustomResponse(
                general_message="IG Chapter not found"
            ).get_failure_response()

        if chapter.lead:
            role = Role.objects.filter(title=f"{chapter.ig.code}CampusLead").first()
            if role:
                UserRoleLink.objects.filter(
                    user=chapter.lead,
                    user__user_organization_link_user__org_id=org_id,
                    user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                    role=role,
                ).delete()
            chapter.lead = None

        chapter.is_active = False
        chapter.updated_by_id = user_id
        chapter.save()

        return CustomResponse(
            general_message="IG Chapter deleted successfully"
        ).get_success_response()


class CampusSocialLinkAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        serializer = serializers.CampusSocialLinkUpsertSerializer(
            data=request.data,
            context={"user_id": user_id, "org": user_org_link.org},
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Social link saved successfully"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def delete(self, request, link_id):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        social_link = CampusSocialLink.objects.filter(
            id=link_id,
            org=user_org_link.org,
        ).first()
        if social_link is None:
            return CustomResponse(
                general_message="Social link not found"
            ).get_failure_response()

        social_link.delete()

        return CustomResponse(
            general_message="Social link deleted successfully"
        ).get_success_response()



class CampusStudentActivityAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request, muid):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(general_message="User have no organization").get_failure_response()

        org_id = user_org_link.org_id
        
        # Verify if the student (muid) belongs to this campus
        try:
            student = User.objects.get(muid=muid)
            is_student_in_campus = UserOrganizationLink.objects.filter(
                user=student, org_id=org_id
            ).exists()
            if not is_student_in_campus:
                return CustomResponse(general_message="Student not found in this campus").get_failure_response()
        except User.DoesNotExist:
            return CustomResponse(general_message="Student not found").get_failure_response()

        from db.task import KarmaActivityLog
        activity_logs = KarmaActivityLog.objects.filter(
            user=student
        ).select_related('task', 'task__ig').order_by('-created_at')

        paginated_queryset = CommonUtils.get_paginated_queryset(activity_logs, request, ["task__title", "task__ig__name"])
        serializer = serializers.StudentActivityTimelineSerializer(paginated_queryset.get('queryset'), many=True)
        
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get('pagination')
        )


class CampusShowcaseAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        org_id = user_org_link.org_id
        try:
            from db.organization import CollegeShowcase
            showcase = CollegeShowcase.objects.get(org_id=org_id)
            serializer = serializers.CampusShowcaseSerializer(showcase)
            return CustomResponse(response=serializer.data).get_success_response()
        except CollegeShowcase.DoesNotExist:
            return CustomResponse(
                general_message="Showcase not found for this campus"
            ).get_failure_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        org_id = user_org_link.org_id
        try:
            from db.organization import CollegeShowcase
            showcase = CollegeShowcase.objects.get(org_id=org_id)
            serializer = serializers.CampusShowcaseSerializer(showcase, data=request.data, partial=True, context={'user_id': user_id, 'org_id': org_id})
        except CollegeShowcase.DoesNotExist:
            serializer = serializers.CampusShowcaseSerializer(data=request.data, context={'user_id': user_id, 'org_id': org_id})

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Campus showcase updated successfully"
            ).get_success_response()
            
        return CustomResponse(
            response=serializer.errors
        ).get_failure_response()