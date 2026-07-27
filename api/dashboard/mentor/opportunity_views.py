from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils
from db.mentor import IgOpportunity, SystemActionLog
from db.user import MentorScopeGrant
from . import opportunity_serializers
from .dash_mentor_helper import get_mentor_scopes, is_mentor_active


def _has_management_access(user_id, opportunity):
    """
    True if the caller created this opportunity, or holds an active
    IG_MENTOR grant for its IG / COMPANY_MENTOR or CAMPUS_MENTOR grant for
    its org.
    """
    if opportunity.created_by_id == user_id:
        return True
    scopes = get_mentor_scopes(user_id)
    if opportunity.ig_id and (MentorScopeGrant.ScopeType.IG_MENTOR, str(opportunity.ig_id)) in scopes:
        return True
    if opportunity.org_id:
        for scope_type in (MentorScopeGrant.ScopeType.COMPANY_MENTOR, MentorScopeGrant.ScopeType.CAMPUS_MENTOR):
            if (scope_type, str(opportunity.org_id)) in scopes:
                return True
    return False


class IgOpportunityListCreateAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Opportunities'],
        description="List opportunities the caller manages (created or scope-matched).",
        responses={200: opportunity_serializers.IgOpportunityListSerializer(many=True)},
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        scopes = get_mentor_scopes(user_id)
        ig_ids = [sid for st, sid in scopes if st == MentorScopeGrant.ScopeType.IG_MENTOR and sid]
        org_ids = [
            sid for st, sid in scopes
            if st in (MentorScopeGrant.ScopeType.COMPANY_MENTOR, MentorScopeGrant.ScopeType.CAMPUS_MENTOR) and sid
        ]

        from django.db.models import Q
        opportunities = IgOpportunity.objects.filter(
            Q(created_by_id=user_id) | Q(ig_id__in=ig_ids) | Q(org_id__in=org_ids)
        ).distinct()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            opportunities, request,
            search_fields=["title", "description", "type", "status"],
            sort_fields={"created_at": "created_at", "title": "title"}
        )
        serializer = opportunity_serializers.IgOpportunityListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={"data": serializer.data, "pagination": paginated_queryset.get("pagination")}
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Mentor Opportunities'],
        description="Create a new opportunity (always starts as DRAFT).",
        request=opportunity_serializers.IgOpportunityCreateSerializer,
        responses={200: opportunity_serializers.IgOpportunityListSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not is_mentor_active(user_id):
            return CustomResponse(general_message="Your mentor account is deactivated and cannot post opportunities.").get_failure_response(status_code=403)

        data = request.data.copy()
        ig_id = data.get('ig')
        org_id = data.get('org')
        scopes = get_mentor_scopes(user_id)

        authorized = (
            (ig_id and (MentorScopeGrant.ScopeType.IG_MENTOR, str(ig_id)) in scopes) or
            (org_id and any(
                (st, str(org_id)) in scopes
                for st in (MentorScopeGrant.ScopeType.COMPANY_MENTOR, MentorScopeGrant.ScopeType.CAMPUS_MENTOR)
            ))
        )
        if not authorized:
            return CustomResponse(general_message="You do not hold an active mentor grant for that IG/org.").get_failure_response(status_code=403)

        serializer = opportunity_serializers.IgOpportunityCreateSerializer(data=data, context={"user_id": user_id})
        if serializer.is_valid():
            opportunity = serializer.save()
            SystemActionLog.objects.create(
                action_type=SystemActionLog.ActionType.OPPORTUNITY_POST,
                actor_user_id=user_id,
                entity_name='ig_opportunity',
                entity_id=opportunity.id,
                new_data={'status': opportunity.status, 'title': opportunity.title},
            )
            return CustomResponse(
                general_message="Opportunity created successfully.",
                response=opportunity_serializers.IgOpportunityListSerializer(opportunity).data,
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class IgOpportunityDetailAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Mentor Opportunities'], responses={200: opportunity_serializers.IgOpportunityListSerializer})
    @role_required([RoleType.MENTOR.value])
    def get(self, request, opportunity_id):
        user_id = JWTUtils.fetch_user_id(request)
        opportunity = IgOpportunity.objects.filter(id=opportunity_id).first()
        if not opportunity or not _has_management_access(user_id, opportunity):
            return CustomResponse(general_message="Opportunity not found.").get_failure_response(status_code=404)
        return CustomResponse(response=opportunity_serializers.IgOpportunityListSerializer(opportunity).data).get_success_response()

    @extend_schema(tags=['Dashboard - Mentor Opportunities'], request=opportunity_serializers.IgOpportunityUpdateSerializer)
    @role_required([RoleType.MENTOR.value])
    def patch(self, request, opportunity_id):
        user_id = JWTUtils.fetch_user_id(request)
        opportunity = IgOpportunity.objects.filter(id=opportunity_id).first()
        if not opportunity or not _has_management_access(user_id, opportunity):
            return CustomResponse(general_message="Opportunity not found.").get_failure_response(status_code=404)

        serializer = opportunity_serializers.IgOpportunityUpdateSerializer(
            opportunity, data=request.data, partial=True, context={"user_id": user_id}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Opportunity updated successfully.",
                response=opportunity_serializers.IgOpportunityListSerializer(opportunity).data,
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @extend_schema(tags=['Dashboard - Mentor Opportunities'])
    @role_required([RoleType.MENTOR.value])
    def delete(self, request, opportunity_id):
        user_id = JWTUtils.fetch_user_id(request)
        opportunity = IgOpportunity.objects.filter(id=opportunity_id).first()
        if not opportunity or not _has_management_access(user_id, opportunity):
            return CustomResponse(general_message="Opportunity not found.").get_failure_response(status_code=404)
        opportunity.status = IgOpportunity.Status.ARCHIVED
        opportunity.updated_by_id = user_id
        opportunity.save(update_fields=["status", "updated_by_id"])
        return CustomResponse(general_message="Opportunity archived successfully.").get_success_response()


class IgOpportunityPublishAPI(APIView):
    """
    POST <id>/publish/ — DRAFT -> PUBLISHED.
    POST <id>/close/   — PUBLISHED -> CLOSED.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Mentor Opportunities'])
    @role_required([RoleType.MENTOR.value])
    def post(self, request, opportunity_id):
        user_id = JWTUtils.fetch_user_id(request)
        opportunity = IgOpportunity.objects.filter(id=opportunity_id).first()
        if not opportunity or not _has_management_access(user_id, opportunity):
            return CustomResponse(general_message="Opportunity not found.").get_failure_response(status_code=404)

        if opportunity.status != IgOpportunity.Status.DRAFT:
            return CustomResponse(general_message="Only draft opportunities can be published.").get_failure_response()

        opportunity.status = IgOpportunity.Status.PUBLISHED
        opportunity.updated_by_id = user_id
        opportunity.save(update_fields=["status", "updated_by_id"])

        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.OPPORTUNITY_POST,
            actor_user_id=user_id,
            entity_name='ig_opportunity',
            entity_id=opportunity.id,
            new_data={'status': opportunity.status},
        )

        return CustomResponse(general_message="Opportunity published successfully.").get_success_response()


class IgOpportunityCloseAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Mentor Opportunities'])
    @role_required([RoleType.MENTOR.value])
    def post(self, request, opportunity_id):
        user_id = JWTUtils.fetch_user_id(request)
        opportunity = IgOpportunity.objects.filter(id=opportunity_id).first()
        if not opportunity or not _has_management_access(user_id, opportunity):
            return CustomResponse(general_message="Opportunity not found.").get_failure_response(status_code=404)

        if opportunity.status != IgOpportunity.Status.PUBLISHED:
            return CustomResponse(general_message="Only published opportunities can be closed.").get_failure_response()

        opportunity.status = IgOpportunity.Status.CLOSED
        opportunity.updated_by_id = user_id
        opportunity.save(update_fields=["status", "updated_by_id"])
        return CustomResponse(general_message="Opportunity closed successfully.").get_success_response()


class PublicIgOpportunityListAPI(APIView):
    permission_classes = []

    @extend_schema(
        tags=['Public - Opportunities'],
        description="Public list of published opportunities, optionally filtered by ig/org.",
        parameters=[
            OpenApiParameter("ig_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("org_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: opportunity_serializers.IgOpportunityListSerializer(many=True)},
    )
    def get(self, request):
        opportunities = IgOpportunity.objects.filter(status=IgOpportunity.Status.PUBLISHED)

        ig_id = request.query_params.get("ig_id")
        org_id = request.query_params.get("org_id")
        if ig_id:
            opportunities = opportunities.filter(ig_id=ig_id)
        if org_id:
            opportunities = opportunities.filter(org_id=org_id)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            opportunities, request,
            search_fields=["title", "description", "type"],
            sort_fields={"created_at": "created_at", "title": "title"}
        )
        serializer = opportunity_serializers.IgOpportunityListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={"data": serializer.data, "pagination": paginated_queryset.get("pagination")}
        ).get_success_response()
