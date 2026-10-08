from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from db.problem_statement import ProblemStatement, ProblemStatementInteraction
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils

from . import serializers, services

TAGS = ["Dashboard - Problem Statements (Learner)"]


def _published():
    """Only published statements are ever visible to learners."""
    return services.statement_queryset().filter(status=ProblemStatement.Status.PUBLISHED)


def _published_or_none(statement_id):
    return _published().filter(id=statement_id).first()


class ProblemStatementListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=TAGS,
        description="List published problem statements. Filters: category, skill, company_id, open_only=true.",
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        qs = _published()
        params = request.query_params
        if params.get("category"):
            qs = qs.filter(category__iexact=params["category"])
        if params.get("skill"):
            qs = qs.filter(skills__contains=[params["skill"]])
        if params.get("company_id"):
            qs = qs.filter(company_id=params["company_id"])
        if params.get("open_only") == "true":
            qs = qs.filter(Q(deadline__isnull=True) | Q(deadline__gt=timezone.now()))
        page = CommonUtils.get_paginated_queryset(
            qs.order_by("-published_at"), request,
            ["title", "description", "category", "company__name"],
            {"published_at": "published_at", "deadline": "deadline", "title": "title"},
        )
        items = list(page["queryset"])
        ids = [s.id for s in items]
        ctx = {
            "counts": services.interaction_counts(ids),
            "my_interactions": services.my_interactions(user_id, ids),
        }
        return CustomResponse(response={
            "data": serializers.ProblemStatementSerializer(items, many=True, context=ctx).data,
            "pagination": page["pagination"],
        }).get_success_response()


class ProblemStatementDetailAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Full details of a published problem statement.")
    def get(self, request, statement_id):
        statement = _published_or_none(statement_id)
        if not statement:
            return services.failure("Problem statement not found.", 404)
        user_id = JWTUtils.fetch_user_id(request)
        ctx = {
            "counts": services.interaction_counts([statement.id]),
            "my_interactions": services.my_interactions(user_id, [statement.id]),
        }
        return CustomResponse(
            response=serializers.ProblemStatementSerializer(statement, context=ctx).data
        ).get_success_response()


class ProblemStatementInteractionAPI(APIView):
    """The caller's own interaction. The user always comes from the JWT, never the body."""
    permission_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Get my interaction with a problem statement.")
    def get(self, request, statement_id):
        statement = _published_or_none(statement_id)
        if not statement:
            return services.failure("Problem statement not found.", 404)
        interaction = ProblemStatementInteraction.objects.filter(
            problem_statement=statement, user_id=JWTUtils.fetch_user_id(request)
        ).first()
        return CustomResponse(response={
            "status": interaction.status if interaction else None,
            "created_at": interaction.created_at if interaction else None,
            "updated_at": interaction.updated_at if interaction else None,
        }).get_success_response()

    @extend_schema(
        tags=TAGS, request=serializers.InteractionWriteSerializer,
        description="Add or change my interaction (one per problem statement).",
    )
    def put(self, request, statement_id):
        statement = _published_or_none(statement_id)
        if not statement:
            return services.failure("Problem statement not found.", 404)
        if statement.deadline and statement.deadline <= timezone.now():
            return services.failure("This problem statement is no longer accepting interactions.", 409)
        serializer = serializers.InteractionWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()
        # update_or_create + the (statement, user) unique key: repeated or
        # concurrent calls end up as one row.
        with transaction.atomic():
            interaction, _ = ProblemStatementInteraction.objects.update_or_create(
                problem_statement=statement,
                user_id=JWTUtils.fetch_user_id(request),
                defaults={"status": serializer.validated_data["status"]},
            )
        counts = services.interaction_counts([statement.id]).get(statement.id, {})
        return CustomResponse(
            general_message="Interaction saved.",
            response={"status": interaction.status, "counts": counts},
        ).get_success_response()

    @extend_schema(tags=TAGS, description="Remove my interaction.")
    def delete(self, request, statement_id):
        statement = _published_or_none(statement_id)
        if not statement:
            return services.failure("Problem statement not found.", 404)
        deleted, _ = ProblemStatementInteraction.objects.filter(
            problem_statement=statement, user_id=JWTUtils.fetch_user_id(request)
        ).delete()
        if not deleted:
            return services.failure("You have no interaction with this problem statement.", 404)
        return CustomResponse(general_message="Interaction removed.").get_success_response()


class ProblemStatementInteractionCountsAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Interaction counts per status.")
    def get(self, request, statement_id):
        statement = _published_or_none(statement_id)
        if not statement:
            return services.failure("Problem statement not found.", 404)
        counts = services.interaction_counts([statement.id]).get(statement.id, {})
        return CustomResponse(response={
            s: counts.get(s, 0) for s in ProblemStatementInteraction.Status.values
        }).get_success_response()
