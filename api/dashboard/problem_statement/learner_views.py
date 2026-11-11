from django.db import IntegrityError, transaction
from django.db.models import BooleanField, Q
from django.db.models.expressions import RawSQL
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from db.problem_statement import ProblemStatement, ProblemStatementInteraction
from db.user import User
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
        description="List published problem statements. "
                    "Filters: category, skill, company_id, source=company|mulearn, open_only=true.",
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        qs = ps_utils.filter_source(_published(), request.query_params)
        params = request.query_params
        if params.get("category"):
            qs = qs.filter(category__iexact=params["category"])
        if params.get("skill"):
            # Compare decoded array values (not JSON text, where quotes and
            # backslashes are escaped), ignoring case like de-duplication on save.
            qs = qs.alias(has_skill=RawSQL(
                "EXISTS (SELECT 1 FROM JSON_TABLE(problem_statement.skills, '$[*]' "
                "COLUMNS (skill VARCHAR(50) PATH '$')) AS s WHERE LOWER(s.skill) = LOWER(%s))",
                [params["skill"].strip()],
                output_field=BooleanField(),
            )).filter(has_skill=True)
        if params.get("company_id"):
            qs = qs.filter(company_id=params["company_id"])
        if params.get("open_only") == "true":
            qs = qs.filter(Q(deadline__isnull=True) | Q(deadline__gt=timezone.now()))
        search_query = params.get("search")
        # "company__name" can't match muLearn-sourced rows (company is null); searching the
        # display label shown for them needs an explicit extra condition.
        extra_q = Q(source=ProblemStatement.Source.MULEARN) if search_query and "mulearn" in search_query.lower() else None
        page = CommonUtils.get_paginated_queryset(
            qs.order_by("-published_at"), request,
            ["title", "description", "category", "company__name"],
            {"published_at": "published_at", "deadline": "deadline", "title": "title"},
            extra_q=extra_q,
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
        return CustomResponse(response=_interaction_payload(interaction)).get_success_response()

    @extend_schema(
        tags=TAGS, request=serializers.InteractionWriteSerializer,
        description="Mark that I am trying this problem statement (one interaction per statement).",
    )
    def put(self, request, statement_id):
        statement = _published_or_none(statement_id)
        if not statement:
            return ps_utils.not_found()
        if ps_utils.deadline_passed(statement):
            return ps_utils.failure("This problem statement is no longer accepting interactions.", 409)
        serializer = serializers.InteractionWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()
        # get_or_create, not update_or_create: "Trying" is the only status accepted
        # here, and an existing Submitted row must not be downgraded (its link would
        # be left behind on a Trying row). The (statement, user) unique key makes
        # repeated or concurrent calls end up as one row.
        user_id = JWTUtils.fetch_user_id(request)
        try:
            with transaction.atomic():
                statement, error = _lock_open_statement(statement_id, "interactions")
                if error:
                    return error
                interaction, _ = ProblemStatementInteraction.objects.get_or_create(
                    problem_statement=statement,
                    user_id=user_id,
                    defaults={"status": ProblemStatementInteraction.Status.TRYING},
                )
        except IntegrityError:
            error = _write_conflict(statement.id, user_id)
            if error:
                return error
            raise
        return CustomResponse(
            general_message="Interaction saved.",
            response={"status": interaction.status, "counts": ps_utils.counts_for(statement.id)},
        ).get_success_response()

    @extend_schema(tags=TAGS, description="Remove my interaction. Works even if the statement was unpublished, "
                                          "except that a submission is locked once the deadline passes.")
    def delete(self, request, statement_id):
        # Not limited to published statements: a learner must always be able to
        # withdraw, otherwise an unpublished-then-republished statement keeps them counted.
        interactions = ProblemStatementInteraction.objects.filter(
            problem_statement_id=statement_id, user_id=JWTUtils.fetch_user_id(request)
        )
        with transaction.atomic():
            if _submission_locked(statement_id, interactions):
                return _locked()
            deleted, _ = interactions.delete()
        if not deleted:
            return ps_utils.failure("You have no interaction with this problem statement.", 404)
        return CustomResponse(general_message="Interaction removed.").get_success_response()


class ProblemStatementSubmissionAPI(APIView):
    """The caller's own submission link. The user always comes from the JWT, never the body."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=TAGS, request=serializers.SubmissionWriteSerializer,
        description="Submit or replace my solution link (https only). Marks me as Submitted; "
                    "allowed until the deadline.",
    )
    def put(self, request, statement_id):
        statement = _published_or_none(statement_id)
        if not statement:
            return ps_utils.not_found()
        if ps_utils.deadline_passed(statement):
            return ps_utils.failure("This problem statement is no longer accepting submissions.", 409)
        serializer = serializers.SubmissionWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()
        user_id = JWTUtils.fetch_user_id(request)
        try:
            with transaction.atomic():
                statement, error = _lock_open_statement(statement_id, "submissions")
                if error:
                    return error
                interaction, _ = ProblemStatementInteraction.objects.update_or_create(
                    problem_statement=statement,
                    user_id=user_id,
                    defaults={
                        "status": ProblemStatementInteraction.Status.SUBMITTED,
                        "submission_url": serializer.validated_data["submission_url"],
                        "submitted_at": timezone.now(),
                    },
                )
        except IntegrityError:
            error = _write_conflict(statement.id, user_id)
            if error:
                return error
            raise
        return CustomResponse(
            general_message="Submission saved.",
            response={**_interaction_payload(interaction), "counts": ps_utils.counts_for(statement.id)},
        ).get_success_response()

    @extend_schema(tags=TAGS, description="Withdraw my submission (back to Trying). Not allowed after the deadline.")
    def delete(self, request, statement_id):
        submissions = ProblemStatementInteraction.objects.filter(
            problem_statement_id=statement_id,
            user_id=JWTUtils.fetch_user_id(request),
            status=ProblemStatementInteraction.Status.SUBMITTED,
        )
        with transaction.atomic():
            if _submission_locked(statement_id, submissions):
                return _locked()
            # .update() skips auto_now, so updated_at is set explicitly.
            updated = submissions.update(
                status=ProblemStatementInteraction.Status.TRYING,
                submission_url=None,
                submitted_at=None,
                updated_at=timezone.now(),
            )
        if not updated:
            return ps_utils.failure("You have no submission for this problem statement.", 404)
        return CustomResponse(general_message="Submission withdrawn.").get_success_response()


def _interaction_payload(interaction):
    return {
        "status": interaction.status if interaction else None,
        "submission_url": interaction.submission_url if interaction else None,
        "submitted_at": interaction.submitted_at if interaction else None,
        "created_at": interaction.created_at if interaction else None,
        "updated_at": interaction.updated_at if interaction else None,
    }


def _write_conflict(statement_id, user_id):
    """
    Response for an IntegrityError on an interaction write, or None to re-raise.
    FK failure: the statement was deleted meanwhile, or the token's user no longer
    exists. Anything else goes to the normal error handler.
    """
    if not ProblemStatement.objects.filter(id=statement_id).exists():
        return ps_utils.not_found()
    if not User.objects.filter(id=user_id).exists():
        return ps_utils.failure("User not found.", 404)
    return None


def _lock_open_statement(statement_id, what):
    """
    (statement, error) inside a transaction: lock the statement, then re-check that
    it is still published and open. The view's earlier check is only a fast path;
    this one runs after any lock wait, so a write can't land after the deadline.
    """
    statement = ps_utils.lock_statement(statement_id)
    if not statement or statement.status != ProblemStatement.Status.PUBLISHED:
        return None, ps_utils.not_found()
    if ps_utils.deadline_passed(statement):
        return None, ps_utils.failure(f"This problem statement is no longer accepting {what}.", 409)
    return statement, None


def _submission_locked(statement_id, interactions):
    """
    A submitted row can't be withdrawn or deleted by the learner after the deadline.
    Must run inside the transaction that then writes: it locks the statement, so the
    deadline can't change and the check can't go stale before the write.
    """
    statement = ps_utils.lock_statement(statement_id)
    if not statement or not ps_utils.deadline_passed(statement):
        return False
    return interactions.filter(status=ProblemStatementInteraction.Status.SUBMITTED).exists()


def _locked():
    return ps_utils.failure("The deadline has passed; your submission can no longer be changed.", 409)


class ProblemStatementInteractionCountsAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Interaction counts per status.")
    def get(self, request, statement_id):
        statement = _published_or_none(statement_id)
        if not statement:
            return ps_utils.not_found()
        return CustomResponse(response=ps_utils.counts_for(statement.id)).get_success_response()
