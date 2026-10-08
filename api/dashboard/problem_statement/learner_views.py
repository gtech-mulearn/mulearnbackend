from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from db.problem_statement import ProblemStatement, ProblemStatementInteraction
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils import problem_statement as ps_utils
from utils.utils import CommonUtils

from . import serializers

TAGS = ["Dashboard - Problem Statements (Learner)"]


def _published():
    """Only published statements are ever visible to learners."""
    return ps_utils.statement_queryset().filter(status=ProblemStatement.Status.PUBLISHED)


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
            # case-insensitive, matching how skills are de-duplicated on save
            qs = qs.filter(skills__icontains=f'"{params["skill"].strip()}"')
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
            "counts": ps_utils.interaction_counts(ids),
            "my_interactions": ps_utils.my_interactions(user_id, ids),
        }
        return CustomResponse().paginated_response(
            data=serializers.ProblemStatementSerializer(items, many=True, context=ctx).data,
            pagination=page["pagination"],
        )


class ProblemStatementDetailAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Full details of a published problem statement.")
    def get(self, request, statement_id):
        statement = _published_or_none(statement_id)
        if not statement:
            return ps_utils.not_found()
        user_id = JWTUtils.fetch_user_id(request)
        ctx = {
            "counts": ps_utils.interaction_counts([statement.id]),
            "my_interactions": ps_utils.my_interactions(user_id, [statement.id]),
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
            return ps_utils.not_found()
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
            return ps_utils.not_found()
        if statement.deadline and statement.deadline <= timezone.now():
            return ps_utils.failure("This problem statement is no longer accepting interactions.", 409)
        serializer = serializers.InteractionWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()
        # update_or_create + the (statement, user) unique key: repeated or
        # concurrent calls end up as one row.
        try:
            with transaction.atomic():
                interaction, _ = ProblemStatementInteraction.objects.update_or_create(
                    problem_statement=statement,
                    user_id=JWTUtils.fetch_user_id(request),
                    defaults={"status": serializer.validated_data.get(
                        "status", ProblemStatementInteraction.Status.TRYING
                    )},
                )
        except IntegrityError:
            # valid token for a user that no longer exists (FK on user_id)
            return ps_utils.failure("User not found.", 404)
        return CustomResponse(
            general_message="Interaction saved.",
            response={"status": interaction.status, "counts": ps_utils.counts_for(statement.id)},
        ).get_success_response()

    @extend_schema(tags=TAGS, description="Remove my interaction. Works even if the statement was unpublished.")
    def delete(self, request, statement_id):
        # Not limited to published statements: a learner must always be able to
        # withdraw, otherwise an unpublished-then-republished statement keeps them counted.
        deleted, _ = ProblemStatementInteraction.objects.filter(
            problem_statement_id=statement_id, user_id=JWTUtils.fetch_user_id(request)
        ).delete()
        if not deleted:
            return ps_utils.failure("You have no interaction with this problem statement.", 404)
        return CustomResponse(general_message="Interaction removed.").get_success_response()


class ProblemStatementInteractionCountsAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Interaction counts per status.")
    def get(self, request, statement_id):
        statement = _published_or_none(statement_id)
        if not statement:
            return ps_utils.not_found()
        return CustomResponse(response=ps_utils.counts_for(statement.id)).get_success_response()
