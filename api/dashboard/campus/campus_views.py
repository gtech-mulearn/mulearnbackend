from django.db.models import Count, F
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from db.organization import Organization, UserOrganizationLink, College, CampusExecom
from db.task import Level, Wallet, InterestGroup
from db.user import User, Role, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from . import serializers
from .dash_campus_helper import get_user_college_link


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


# Campus Execom Management APIs

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_campus_execom(request, college_id):
    """
    GET /api/campus/:id/execom
    View all executive committee members for a specific college
    """
    try:
        college = get_object_or_404(College, id=college_id)
        
        # Get all execom members for this college
        execom_members = CampusExecom.objects.filter(college=college).select_related('user', 'college__org')
        
        # Format the response
        members_data = []
        for member in execom_members:
            members_data.append({
                'uid': member.user.id,
                'name': member.user.full_name,
                'email': member.user.email,
                'role': member.role,
                'added_at': member.created_at.isoformat(),
            })
        
        return CustomResponse(
            response={
                'college': {
                    'id': college.id,
                    'name': college.org.title,
                    'code': college.org.code,
                },
                'execom_members': members_data,
                'total_members': len(members_data)
            }
        ).get_success_response()
        
    except Exception as e:
        return CustomResponse(
            general_message=f'Error fetching execom members: {str(e)}'
        ).get_failure_response()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_execom_member(request, college_id):
    """
    POST /api/campus/:id/execom
    Add a new member to the executive committee
    
    Expected payload:
    {
        "user_id": "uuid",
        "role": "President"
    }
    """
    try:
        college = get_object_or_404(College, id=college_id)
        
        # Get data from request
        user_id = request.data.get('user_id')
        role = request.data.get('role')
        
        # Validate required fields
        if not user_id or not role:
            return CustomResponse(
                general_message='user_id and role are required fields'
            ).get_failure_response()
        
        # Validate user exists
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return CustomResponse(
                general_message='User not found'
            ).get_failure_response()
        
        # Validate role length
        if len(role) > 100:
            return CustomResponse(
                general_message='Role name too long (max 100 characters)'
            ).get_failure_response()
        
        # Check if this combination already exists
        if CampusExecom.objects.filter(college=college, user=user, role=role).exists():
            return CustomResponse(
                general_message='This user already has this role in this college execom'
            ).get_failure_response()
        
        # Create execom member
        execom_member = CampusExecom.objects.create(
            college=college,
            user=user,
            role=role,
            created_by=request.user,
            updated_by=request.user
        )
        
        return CustomResponse(
            general_message='Execom member added successfully',
            response={
                'id': execom_member.id,
                'user': {
                    'id': user.id,
                    'name': user.full_name,
                    'email': user.email,
                },
                'role': execom_member.role,
                'added_at': execom_member.created_at.isoformat(),
            }
        ).get_success_response()
        
    except Exception as e:
        return CustomResponse(
            general_message=f'Error adding execom member: {str(e)}'
        ).get_failure_response()


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_execom_member(request, college_id, uid):
    """
    DELETE /api/campus/:id/execom/:uid
    Remove a member from the executive committee
    """
    try:
        college = get_object_or_404(College, id=college_id)
        
        # Find the execom member
        try:
            execom_member = CampusExecom.objects.get(
                college=college,
                user__id=uid
            )
        except CampusExecom.DoesNotExist:
            return CustomResponse(
                general_message='Execom member not found'
            ).get_failure_response()
        
        # Store member info before deletion
        member_name = execom_member.user.full_name
        member_role = execom_member.role
        
        # Delete the member
        execom_member.delete()
        
        return CustomResponse(
            general_message=f'Successfully removed {member_name} from {member_role} position'
        ).get_success_response()
        
    except Exception as e:
        return CustomResponse(
            general_message=f'Error removing execom member: {str(e)}'
        ).get_failure_response()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users_for_execom(request):
    """
    GET /api/users/search?q=query
    Search for users to add to execom
    """
    try:
        query = request.GET.get('q', '')
        
        if len(query) < 2:
            return CustomResponse(
                general_message='Query must be at least 2 characters long'
            ).get_failure_response()
        
        # Search users by email, full_name, or muid
        users = User.objects.filter(
            Q(email__icontains=query) |
            Q(full_name__icontains=query) |
            Q(muid__icontains=query)
        )[:50]  # Limit to 50 results
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'name': user.full_name,
                'email': user.email,
                'muid': user.muid,
            })
        
        return CustomResponse(
            response=users_data
        ).get_success_response()
        
    except Exception as e:
        return CustomResponse(
            general_message=f'Error searching users: {str(e)}'
        ).get_failure_response()
