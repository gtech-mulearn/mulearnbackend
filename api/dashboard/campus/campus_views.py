from django.db.models import Count, F,Sum, Subquery, OuterRef, IntegerField
from django.db.models.functions import Coalesce
from django.db.models import Q
from django.db import transaction
from rest_framework.views import APIView
from collections import defaultdict
import uuid
from db.organization import Organization, UserOrganizationLink
from db.task import Level, Wallet, InterestGroup, UserIgLink
from db.campus import CampusIGChapter, CampusSocialLink
from db.learning_circle import UserCircleLink
from db.user import User, Role, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from . import serializers
from .dash_campus_helper import get_user_college_link, get_campus_ig_chapters, campus_staff_required, assign_ig_campus_lead
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiResponse
from rest_framework import serializers as s


class CampusListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus List.",
        responses={200: serializers.CampusListSerializer},
    )
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
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus Details Public.",
        responses={200: serializers.CampusDetailsPublicSerializer},
    )
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

    @campus_staff_required
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus Details.",
        responses={200: serializers.CampusDetailsSerializer},
    )
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
    @extend_schema(tags=['Dashboard - Campus'], description="Retrieve Campus Student In Each Level.",
        responses={200: inline_serializer(
            name="CampusStudentInEachLevelResponse",
            fields={
                "hasError": s.BooleanField(),
                "statusCode": s.IntegerField(),
                "message": s.DictField(),
                "response": inline_serializer(
                    name="CampusStudentLevelItem",
                    fields={
                        "level": s.IntegerField(),
                        "students": s.IntegerField(),
                    },
                    many=True,
                ),
            },
        )},
    )
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
                    user_lvl_link_level__user__user_organization_link_user__org=org,
                    user_lvl_link_level__user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                    user_lvl_link_level__user__user_organization_link_user__verified=True,
                ),
                distinct=True,
            )
        ).values(level=F("level_order"), students=F("students"))

        return CustomResponse(response=level_with_student_count).get_success_response()


class CampusStudentDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @campus_staff_required
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus Student Details.",
        responses={200: serializers.CampusStudentDetailsSerializer},
    )
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

        # Build dynamic filters from query params
        is_alumni = request.query_params.get("is_alumni")
        ig = request.query_params.get("ig")
        category = request.query_params.get("category")

        wallet_filters = Q(
            user__user_organization_link_user__org=user_org_link.org,
            user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user__user_organization_link_user__verified=True,
        )
        user_filters = Q(
            user_organization_link_user__org=user_org_link.org,
            user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user_organization_link_user__verified=True,
        )

        if is_alumni is not None:
            is_alumni_filter = str(is_alumni).lower() == "true"
            wallet_filters &= Q(user__user_organization_link_user__is_alumni=is_alumni_filter)
            user_filters &= Q(user_organization_link_user__is_alumni=is_alumni_filter)

        if ig is not None:
            wallet_filters &= Q(user__user_ig_link_user__ig__id=ig)
            user_filters &= Q(user_ig_link_user__ig__id=ig)

        if category is not None:
            wallet_filters &= Q(user__user_ig_link_user__ig__category=category)
            user_filters &= Q(user_ig_link_user__ig__category=category)

        rank = (
            Wallet.objects.filter(wallet_filters)
            .distinct()
            .order_by("-karma", "-created_at")
            .values("user_id", "karma")
        )
        ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

        # Correlated subqueries (not joined Counts) so they can't be inflated
        # by the ig_id/category .filter() calls applied to user_filters above,
        # which also traverse user_ig_link_user.
        ig_count_sq = (
            UserIgLink.objects.filter(
                user_id=OuterRef("pk"),
                is_active=True,
                assignment_type=UserIgLink.AssignmentType.LEARNER,
            )
            .values("user_id")
            .annotate(count=Count("id", distinct=True))
            .values("count")
        )
        lc_count_sq = (
            UserCircleLink.objects.filter(user_id=OuterRef("pk"), accepted=True)
            .values("user_id")
            .annotate(count=Count("id", distinct=True))
            .values("count")
        )

        user_org_links = (
            User.objects.filter(user_filters)
            .distinct()
            .annotate(
                user_id=F("id"),
                email_=F("email"),
                mobile_=F("mobile"),
                karma=F("wallet_user__karma"),
                level=F("user_lvl_link_user__level__name"),
                join_date=F("user_organization_link_user__created_at"),  # org join date, not account signup date
                last_karma_gained=F("wallet_user__karma_last_updated_at"),
                department=F("user_organization_link_user__department__title"),
                graduation_year=F("user_organization_link_user__graduation_year"),
                is_alumni=F("user_organization_link_user__is_alumni"),
                ig_count=Coalesce(Subquery(ig_count_sq, output_field=IntegerField()), 0),
                lc_count=Coalesce(Subquery(lc_count_sq, output_field=IntegerField()), 0),
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
                "join_date": "user_organization_link_user__created_at",
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

    @campus_staff_required
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus Student Details CSV.",
        responses={200: serializers.CampusStudentDetailsSerializer},
    )
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

        # Build dynamic filters from query params
        is_alumni = request.query_params.get("is_alumni")
        ig = request.query_params.get("ig")
        category = request.query_params.get("category")

        wallet_filters = Q(
            user__user_organization_link_user__org=user_org_link.org,
            user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user__user_organization_link_user__verified=True,
        )
        user_filters = Q(
            user_organization_link_user__org=user_org_link.org,
            user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user_organization_link_user__verified=True,
        )

        if is_alumni is not None:
            is_alumni_filter = str(is_alumni).lower() == "true"
            wallet_filters &= Q(user__user_organization_link_user__is_alumni=is_alumni_filter)
            user_filters &= Q(user_organization_link_user__is_alumni=is_alumni_filter)

        if ig is not None:
            wallet_filters &= Q(user__user_ig_link_user__ig__id=ig)
            user_filters &= Q(user_ig_link_user__ig__id=ig)

        if category is not None:
            wallet_filters &= Q(user__user_ig_link_user__ig__category=category)
            user_filters &= Q(user_ig_link_user__ig__category=category)

        rank = (
            Wallet.objects.filter(wallet_filters)
            .distinct()
            .order_by("-karma", "-created_at")
            .values("user_id", "karma")
        )
        ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

        ig_count_sq = (
            UserIgLink.objects.filter(
                user_id=OuterRef("pk"),
                is_active=True,
                assignment_type=UserIgLink.AssignmentType.LEARNER,
            )
            .values("user_id")
            .annotate(count=Count("id", distinct=True))
            .values("count")
        )
        lc_count_sq = (
            UserCircleLink.objects.filter(user_id=OuterRef("pk"), accepted=True)
            .values("user_id")
            .annotate(count=Count("id", distinct=True))
            .values("count")
        )

        user_org_links = (
            User.objects.filter(user_filters)
            .distinct()
            .annotate(
                user_id=F("id"),
                email_=F("email"),
                mobile_=F("mobile"),
                karma=F("wallet_user__karma"),
                level=F("user_lvl_link_user__level__name"),
                join_date=F("user_organization_link_user__created_at"),  # org join date, not account signup date
                last_karma_gained=F("wallet_user__karma_last_updated_at"),
                department=F("user_organization_link_user__department__title"),
                graduation_year=F("user_organization_link_user__graduation_year"),
                is_alumni=F("user_organization_link_user__is_alumni"),
                ig_count=Coalesce(Subquery(ig_count_sq, output_field=IntegerField()), 0),
                lc_count=Coalesce(Subquery(lc_count_sq, output_field=IntegerField()), 0),
            )
        )

        filtered_queryset = CommonUtils.get_paginated_queryset(
            user_org_links,
            request,
            ["full_name", "level"],
            {
                "full_name": "full_name",
                "muid": "muid",
                "karma": "wallet_user__karma",
                "level": "user_lvl_link_user__level__level_order",
                # "is_active": "karma_activity_log_user__created_at",
                "join_date": "user_organization_link_user__created_at",
                "email": "email_",
                "mobile": "mobile_",
                "is_alumni": "is_alumni",
            },
            is_pagination=False,
        )

        serializer = serializers.CampusStudentDetailsSerializer(
            filtered_queryset, many=True, context={"ranks": ranks}
        )
        return CommonUtils.generate_csv(serializer.data, "Campus Student Details")


class WeeklyKarmaAPI(APIView):
    authentication_classes = [CustomizePermission]

    # @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Weekly Karma.",
        responses={200: serializers.WeeklyKarmaSerializer},
    )
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
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Partially update Change Student Type.",
        responses={200: serializers.ChangeStudentTypeSerializer},
    )
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
    @role_required([RoleType.CAMPUS_LEAD.value,RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Create Transfer Lead Role.",
        request=serializers.UserRoleLinkSerializer,
        responses={200: serializers.UserRoleLinkSerializer},
    )
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

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Create Transfer Enabler Role.",
        request=serializers.UserRoleLinkSerializer,
        responses={200: serializers.UserRoleLinkSerializer},
    )
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
    @extend_schema(tags=['Dashboard - Campus'], description="Retrieve Transfer I G Role.",
        responses={200: serializers.UserRoleLinkSerializer},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()
        ig_list = (
            CampusIGChapter.objects.filter(
                org=user_org_link.org,
                is_active=True,
            )
            .values_list("ig__code", flat=True)
            .distinct()
        )

        return CustomResponse(response={"ig_list": ig_list}).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Create Transfer I G Role.",
        request=serializers.UserRoleLinkSerializer,
        responses={200: serializers.UserRoleLinkSerializer},
    )
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

        chapter = CampusIGChapter.objects.filter(
            org=user_org_link.org,
            ig__code=ig_code
        ).first()

        if not chapter:
            return CustomResponse(
                general_message="Interest Group chapter not found in your campus"
            ).get_failure_response()

        if UserRoleLink.objects.filter(user=new_ig, role__title=RoleType.IG_CAMPUS_LEAD_ROLE(ig_code)).exists():
            return CustomResponse(
                general_message="User already has this role."
            ).get_failure_response()

        with transaction.atomic():
            assign_ig_campus_lead(chapter, new_ig, user_id)

        return CustomResponse(
            general_message="Assigned new IG Campus Lead successfully"
        ).get_success_response()

# ...existing code...

class CampusStudentListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @campus_staff_required
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve a lightweight list of students (full_name, muid, profile_pic) for the authenticated user's college.",
        responses={200: serializers.CampusStudentListSerializer(many=True)},
    )
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

        qs = (
            User.objects.filter(
                user_organization_link_user__org=org,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            )
            .distinct()
            .annotate(
                full_name=F("full_name"),
                muid=F("muid"),
                profile_pic=F("profile_pic"),
            )
            .order_by("full_name")
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            qs,
            request,
            search_fields=["full_name", "muid"],
            sort_fields={
                "full_name": "full_name",
                "muid": "muid",
            },
        )

        serializer = serializers.CampusStudentListSerializer(
            paginated_queryset.get("queryset"),
            many=True,
        )

        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class CampusStudentLeaderboardAPI(APIView):

    authentication_classes = [CustomizePermission]
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus Student Leaderboard.",
        responses={200: serializers.CampusLeaderboardSerializer},
    )
    def get(self, request, org_id=None):

        if not org_id:
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
        else:
            org = Organization.objects.filter(
                id=org_id,
                org_type=OrganizationType.COLLEGE.value
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
                user__user_organization_link_user__verified=True,
            )
            .distinct()
            .order_by("-karma","-created_at")
            .values("user_id")
        )
        ranks = {r["user_id"]: i + 1 for i, r in enumerate(rank_qs)}


        # 2. Base queryset - all students with annotations                    #

        ig_count_subquery = (
            UserIgLink.objects.filter(
                user_id=OuterRef("id"),
                is_active=True,
                assignment_type=UserIgLink.AssignmentType.LEARNER,
            )
            .values("user_id")
            .annotate(count=Count("id", distinct=True))
            .values("count")
        )

        qs = (
            User.objects.filter(
                user_organization_link_user__org=org,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                user_organization_link_user__verified=True,
            )
            .distinct()
            .annotate(
                user_id=F("id"),
                # existing fields from CampusStudentDetailsAPI
                karma=F("wallet_user__karma"),
                level=F("user_lvl_link_user__level__name"),
                join_date=F("user_organization_link_user__created_at"),  # org join date, not account signup date
                last_karma_gained=F("wallet_user__karma_last_updated_at"),
                department=F("user_organization_link_user__department__title"),
                graduation_year=F("user_organization_link_user__graduation_year"),
                is_alumni=F("user_organization_link_user__is_alumni"),

                # new fields not in existing API
                # Computed as a correlated subquery (not a joined Count) so it can't be
                # inflated by the ig_id/category .filter() calls added below, which also
                # traverse user_ig_link_user and would otherwise fan out the join.
                ig_count=Coalesce(Subquery(ig_count_subquery, output_field=IntegerField()), 0),
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
        # No default is_alumni filter: every campus member (alumni
        # included) appears on the leaderboard unless ?is_alumni= is passed.
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
                "join_date":       "user_organization_link_user__created_at",
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

    @extend_schema(tags=['Dashboard - Campus'], description="Retrieve Campus Karma By Cluster.",
        responses={200: inline_serializer(
            name="CampusKarmaByClusterResponse",
            fields={
                "hasError": s.BooleanField(),
                "statusCode": s.IntegerField(),
                "message": s.DictField(),
                "response": inline_serializer(
                    name="CampusKarmaByClusterCategory",
                    fields={
                        "total_karma": s.IntegerField(),
                        "member_count": s.IntegerField(),
                    },
                ),
            },
        )},
    )
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

        # Subquery: each user's single "primary" category — their earliest
        # active LEARNER IG membership (mentor/lead/moderator assignments are
        # staff roles, not personal category membership, so they're excluded
        # here just like every other IG-membership count in this app). A
        # member can belong to IGs spanning several categories; without
        # picking exactly one, their full karma would get added to every
        # category they touch, making the bucket totals sum to several times
        # the campus's actual total_karma.
        primary_category_sq = (
            UserIgLink.objects.filter(
                user_id=OuterRef("pk"),
                is_active=True,
                assignment_type=UserIgLink.AssignmentType.LEARNER,
            )
            .order_by("created_at")
            .values("ig__category")[:1]
        )

        # Single query — LEFT JOIN via isnull=False removed
        # users with NO IG will have category=None → goes to "unclustered"
        all_rows = (
            User.objects.filter(
                user_organization_link_user__org=org,
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                user_organization_link_user__verified=True,
            )
            .annotate(
                user_karma=Subquery(wallet_karma_sq),
                primary_category=Subquery(primary_category_sq),
            )
            .values("id", "primary_category", "user_karma")
            .distinct()   # 1 row per user — each user has exactly one primary_category
        )

        # Aggregate in Python
        category_map = defaultdict(lambda: {"total_karma": 0, "member_count": 0, "seen_users": set()})

        for row in all_rows:  # streams from DB — no list() memory spike
            category = row["primary_category"] or "unclustered"
            user_id  = row["id"]
            karma    = row["user_karma"] or 0

            # seen_users guards against edge case where a user appears more
            # than once due to multiple org links
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

    @campus_staff_required
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus I G Chapter.",
        responses={200: serializers.CampusIGChapterListSerializer},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        chapters = get_campus_ig_chapters(user_org_link.org.id)
        serializer = serializers.CampusIGChapterListSerializer(chapters, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Create Campus I G Chapter.",
        request=serializers.CampusIGChapterCreateSerializer,
        responses={200: serializers.CampusIGChapterListSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        serializer = serializers.CampusIGChapterCreateSerializer(
            data=request.data,
            context={"user_id": user_id, "org": user_org_link.org},
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="IG Chapter created successfully"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Partially update Campus I G Chapter.",
        responses={200: serializers.CampusIGChapterUpdateSerializer},
    )
    def patch(self, request, chapter_id):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        chapter = CampusIGChapter.objects.filter(
            id=chapter_id,
            org=user_org_link.org,
        ).first()
        if chapter is None:
            return CustomResponse(
                general_message="IG Chapter not found"
            ).get_failure_response()

        serializer = serializers.CampusIGChapterUpdateSerializer(
            chapter,
            data=request.data,
            partial=True,
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="IG Chapter updated successfully"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(tags=['Dashboard - Campus'], description="Delete Campus I G Chapter.",
        responses={200: serializers.CampusIGChapterListSerializer},
    )
    def delete(self, request, chapter_id):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        chapter = CampusIGChapter.objects.filter(
            id=chapter_id,
            org=user_org_link.org,
        ).first()
        if chapter is None:
            return CustomResponse(
                general_message="IG Chapter not found"
            ).get_failure_response()

        if chapter.lead:
            role = Role.objects.filter(
                title=RoleType.IG_CAMPUS_LEAD_ROLE(chapter.ig.code)
            ).first()
            if role:
                UserRoleLink.objects.filter(
                    user=chapter.lead,
                    user__user_organization_link_user__org=user_org_link.org,
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
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Update Campus Social Link.",
        request=serializers.CampusSocialLinkUpsertSerializer,
        responses={200: serializers.CampusSocialLinkUpsertSerializer},
    )
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
    @extend_schema(tags=['Dashboard - Campus'], description="Delete Campus Social Link.",
        responses={200: serializers.CampusSocialLinkUpsertSerializer},
    )
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

    @campus_staff_required
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus Student Activity.",
        responses={200: serializers.StudentActivityTimelineSerializer},
    )
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

    @campus_staff_required
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Retrieve Campus Showcase.",
        responses={200: serializers.CampusShowcaseSerializer},
    )
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
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Partially update Campus Showcase.",
        request=serializers.CampusShowcaseSerializer,
        responses={200: serializers.CampusShowcaseSerializer},
    )
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


class AssignCampusMentorAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    @extend_schema(
        tags=['Dashboard - Campus'],
        description="Assign a student from the campus as a Campus Mentor.",
        request=inline_serializer(
            name="AssignCampusMentorRequest",
            fields={
                "muid": s.CharField(required=True),
            }
        ),
        responses={200: OpenApiResponse(description="Successfully nominated as a Campus Mentor")},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        muid = request.data.get("muid")

        if not muid:
            return CustomResponse(
                general_message="muid is required"
            ).get_failure_response()

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        org = user_org_link.org

        student = User.objects.filter(muid=muid).first()
        if not student:
            return CustomResponse(
                general_message="Student not found"
            ).get_failure_response()

        # Validate student is in the same campus
        student_org_link = UserOrganizationLink.objects.filter(
            user=student,
            org=org,
            org__org_type=OrganizationType.COLLEGE.value,
            is_alumni=False
        ).first()

        if not student_org_link:
            return CustomResponse(
                general_message="Student is not a member of your campus"
            ).get_failure_response()

        from datetime import timedelta
        from db.user import UserMentor, MentorApplication, MentorScopeGrant
        from utils.utils import DateTimeUtils

        existing_pending = MentorApplication.objects.filter(
            user=student,
            tier=UserMentor.MentorTier.CAMPUS_MENTOR,
            org=org,
            status=MentorApplication.Status.PENDING,
        ).exists()
        already_granted = MentorScopeGrant.objects.filter(
            mentor__user=student,
            scope_type=MentorScopeGrant.ScopeType.CAMPUS_MENTOR,
            scope_id=str(org.id),
            is_active=True,
        ).exists()
        if existing_pending or already_granted:
            return CustomResponse(
                general_message="Student is already a Campus Mentor or has a pending request"
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        # Lead nomination pre-approves the tier/scope but still needs admin
        # sign-off before it's live (PRD §4 point 5 — unlike COMPANY_MENTOR,
        # every other tier keeps the admin gate).
        MentorApplication.objects.create(
            user=student,
            tier=UserMentor.MentorTier.CAMPUS_MENTOR,
            org=org,
            source=MentorApplication.SourceType.LEAD_NOMINATED,
            nominated_by_id=user_id,
            status=MentorApplication.Status.PENDING,
            nomination_expires_at=now + timedelta(days=14),
            created_by_id=user_id,
            updated_by_id=user_id,
            created_at=now,
            updated_at=now,
        )

        try:
            from api.notification.notifications_utils import NotificationUtils
            from django.conf import settings
            actor = User.objects.filter(id=user_id).first()
            NotificationUtils.insert_notification(
                user=student,
                title="Campus Mentor Nomination Received",
                description=f"You have been nominated as a Campus Mentor for {org.title}. Awaiting admin approval.",
                button="View",
                url=f"{settings.FR_DOMAIN_NAME}/dashboard/mentor/status/",
                created_by=actor,
            )
        except Exception:
            pass

        return CustomResponse(
            general_message="Student successfully nominated as a Campus Mentor"
        ).get_success_response()
