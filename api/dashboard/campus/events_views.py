from collections import Counter

from django.db.models import Q
from rest_framework.views import APIView

from db.organization import UserOrganizationLink
from db.user import User, Role, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils
from . import serializers as campus_serializers
from .dash_campus_helper import (
    get_user_college_link,
    get_campus_events_qs,
    validate_campus_member,
)


class CampusEventsAPI(APIView):
    """
    GET  campus/events/
    Returns paginated campus-scoped and campus-IG-scoped events
    for the authenticated campus lead's campus.
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org
        events = get_campus_events_qs(org)

        params = request.query_params

        if status := params.get("status"):
            events = events.filter(status=status)

        if scope := params.get("scope"):
            events = events.filter(scope=scope)

        if event_type := params.get("event_type"):
            events = events.filter(organiser_type=event_type)

        if date_from := params.get("date_from"):
            events = events.filter(start_datetime__date__gte=date_from)

        if date_to := params.get("date_to"):
            events = events.filter(start_datetime__date__lte=date_to)

        paginated = CommonUtils.get_paginated_queryset(
            events,
            request,
            search_fields=["title"],
            sort_fields={
                "start_datetime": "start_datetime",
                "interest_count": "interest_count",
            },
        )

        serializer = campus_serializers.CampusEventListSerializer(
            paginated["queryset"], many=True
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated["pagination"],
            }
        ).get_success_response()


class CampusEventDistributionAPI(APIView):
    """
    GET  campus/events/distribution/
    Returns ranked tag distribution for all campus events.
    Aggregates from Event.tags JSONField using Counter.
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org
        tags_qs = get_campus_events_qs(org).values_list("tags", flat=True)

        counter = Counter()
        for tags in tags_qs:
            if tags:  # tags is a JSONField, can be null
                counter.update(tags)

        data = [
            {"tag": tag, "event_count": count}
            for tag, count in counter.most_common()
        ]

        return CustomResponse(
            response={"data": data}
        ).get_success_response()


class CampusExecomAPI(APIView):
    """
    GET     campus/execom/              — list all execom role holders
    POST    campus/execom/              — appoint a member to a role
    DELETE  campus/execom/<member_id>/  — remove a role link
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        if user_org_link.org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()

        org = user_org_link.org

        campus_user_ids = UserOrganizationLink.objects.filter(
            org=org,
            org__org_type=OrganizationType.COLLEGE.value,
        ).values_list("user_id", flat=True)

        execom_links = UserRoleLink.objects.filter(
            user_id__in=campus_user_ids
        ).filter(
            Q(role__title=RoleType.CAMPUS_LEAD.value)
            | Q(role__title=RoleType.LEAD_ENABLER.value)
            | Q(role__title=RoleType.ENABLER.value)
            | Q(role__title__endswith="CampusLead")  # IG roles — no space
        ).select_related("user", "role")

        serializer = campus_serializers.ExecomMemberSerializer(
            execom_links, many=True
        )
        return CustomResponse(
            response={"data": serializer.data}
        ).get_success_response()

    @role_required([RoleType.CAMPUS_LEAD.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        muid = request.data.get("muid")
        role_title = request.data.get("role_title")

        if not muid or not role_title:
            return CustomResponse(
                general_message="muid and role_title are required"
            ).get_failure_response()

        # Fetch user by muid
        new_user = User.objects.filter(muid=muid).first()
        if new_user is None:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()

        # Get requester's campus
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        org = user_org_link.org
        if org is None:
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        # Validate new user is a non-alumni campus member
        if not validate_campus_member(new_user.id, org):
            return CustomResponse(
                general_message="User is not a member of your campus"
            ).get_failure_response()

        # Fetch role by title
        role = Role.objects.filter(title=role_title).first()
        if role is None:
            return CustomResponse(
                general_message="Role not found"
            ).get_failure_response()

        # Remove existing holder of this role in the campus
        campus_user_ids = UserOrganizationLink.objects.filter(
            org=org,
            org__org_type=OrganizationType.COLLEGE.value,
        ).values_list("user_id", flat=True)

        UserRoleLink.objects.filter(
            user_id__in=campus_user_ids,
            role=role,
        ).delete()

        # Assign new role — follows UserRoleLinkSerializer pattern
        serializer = campus_serializers.UserRoleLinkSerializer(
            data={"user": new_user.id, "role": role.id},
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Role assigned successfully"
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.CAMPUS_LEAD.value])
    def delete(self, request, member_id=None):
        user_id = JWTUtils.fetch_user_id(request)

        if not member_id:
            return CustomResponse(
                general_message="member_id is required"
            ).get_failure_response()

        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User has no organization"
            ).get_failure_response()

        org = user_org_link.org

        if org is None:
            return CustomResponse(
                general_message="Campus lead has no college"
            ).get_failure_response()
        # Fetch the role link
        role_link = UserRoleLink.objects.filter(
            id=member_id
        ).select_related("role").first()

        if role_link is None:
            return CustomResponse(
                general_message="Role link not found"
            ).get_failure_response()

        # Guard: must belong to this campus
        campus_user_ids = UserOrganizationLink.objects.filter(
            org=org,
            org__org_type=OrganizationType.COLLEGE.value,
        ).values_list("user_id", flat=True)

        if role_link.user_id not in campus_user_ids:
            return CustomResponse(
                general_message="Role link not found or not part of this campus"
            ).get_failure_response()

        # Guard: campus lead cannot remove their own lead role
        if (
            role_link.user_id == user_id
            and role_link.role.title == RoleType.CAMPUS_LEAD.value
        ):
            return CustomResponse(
                general_message="Cannot remove your own Campus Lead role. Use transfer-lead-role instead."
            ).get_failure_response()

        role_link.delete()
        return CustomResponse(
            general_message="Role removed successfully"
        ).get_success_response()
