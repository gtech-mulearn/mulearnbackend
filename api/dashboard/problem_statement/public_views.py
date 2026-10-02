"""
Public and Learner Problem Statement API views.
Provides unauthenticated public listing & detail view, and authenticated learner interest workflow.
"""
import uuid
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Q
from rest_framework.views import APIView
from rest_framework import status
from drf_spectacular.utils import extend_schema

from db.problem_statement import (
    ProblemStatement,
    ProblemStatementInterest,
)
from utils.permission import CustomizePermission, OptionalAuthentication, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils
from utils.types import RoleType

from .serializers import (
    ProblemStatementListItemSerializer,
    ProblemStatementDetailSerializer,
    ProblemStatementInterestSerializer,
)


def _safe_int(value):
    """Safely attempt to convert a string to int without raising ValueError for unicode digits like ²."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _is_learner_role(roles):
    """
    Returns True if caller is not exclusively a Company user.
    """
    if isinstance(roles, list):
        if len(roles) == 1 and roles[0] == RoleType.COMPANY.value:
            return False
    elif isinstance(roles, str) and roles == RoleType.COMPANY.value:
        return False
    return True


class ProblemStatementListAPI(APIView):
    """
    GET /api/v1/dashboard/problem-statements/
    Public feed of published problem statements.
    Uses OptionalAuthentication so logged-in learners receive viewer_interested indicator.
    """
    authentication_classes = [OptionalAuthentication]

    @extend_schema(
        tags=['Problem Statement'],
        description="Public feed of published problem statements with optional category, skill, difficulty, and reward filters.",
    )
    def get(self, request):
        queryset = ProblemStatement.objects.filter(
            status=ProblemStatement.Status.PUBLISHED,
            deleted_at__isnull=True,
        ).select_related('company')

        if category := request.query_params.get('category'):
            cat_int = _safe_int(category)
            if cat_int is not None:
                queryset = queryset.filter(Q(categories__contains=cat_int) | Q(categories__contains=category))
            else:
                queryset = queryset.filter(categories__contains=category)

        if skill := request.query_params.get('skill'):
            skill_int = _safe_int(skill)
            if skill_int is not None:
                queryset = queryset.filter(Q(skills__contains=skill_int) | Q(skills__contains=skill))
            else:
                queryset = queryset.filter(skills__contains=skill)

        if difficulty := request.query_params.get('difficulty'):
            queryset = queryset.filter(difficulty=difficulty)
        if reward_type := request.query_params.get('reward_type'):
            queryset = queryset.filter(reward_type=reward_type)

        paginated = CommonUtils.get_paginated_queryset(
            queryset,
            request,
            search_fields=['title', 'summary', 'description'],
            sort_fields={'created_at': 'created_at', 'deadline': 'deadline', 'title': 'title'},
        )

        user_id = None
        interested_ps_ids = set()
        if JWTUtils.is_logged_in(request):
            user_id = JWTUtils.fetch_user_id(request)
            ps_ids = [ps.id for ps in paginated['queryset']]
            if user_id and ps_ids:
                interested_ps_ids = set(
                    ProblemStatementInterest.objects.filter(
                        problem_statement_id__in=ps_ids,
                        user_id=user_id,
                        status=ProblemStatementInterest.Status.INTERESTED,
                    ).values_list('problem_statement_id', flat=True)
                )

        serialized_data = []
        for ps in paginated['queryset']:
            item_data = ProblemStatementListItemSerializer(ps, context={'request': request}).data
            item_data['viewer_interested'] = ps.id in interested_ps_ids
            serialized_data.append(item_data)

        return CustomResponse().paginated_response(
            data=serialized_data,
            pagination=paginated['pagination'],
        )


class ProblemStatementDetailAPI(APIView):
    """
    GET /api/v1/dashboard/problem-statements/<ps_id>/
    Public detail view of a published problem statement.
    Increments view_count atomically using F() expression.
    """
    authentication_classes = [OptionalAuthentication]

    @extend_schema(
        tags=['Problem Statement'],
        description="Public detail view for a published problem statement. Increments view_count atomically.",
    )
    def get(self, request, ps_id):
        ps = ProblemStatement.objects.filter(
            id=ps_id,
            status=ProblemStatement.Status.PUBLISHED,
            deleted_at__isnull=True,
        ).select_related('company', 'created_by', 'updated_by').first()

        if not ps:
            return CustomResponse(
                general_message="Problem Statement not found."
            ).get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)

        # Atomic view_count increment
        ProblemStatement.objects.filter(id=ps_id).update(view_count=F('view_count') + 1)
        ps.refresh_from_db(fields=['view_count'])

        viewer_interested = False
        if JWTUtils.is_logged_in(request):
            user_id = JWTUtils.fetch_user_id(request)
            if user_id:
                viewer_interested = ProblemStatementInterest.objects.filter(
                    problem_statement=ps,
                    user_id=user_id,
                    status=ProblemStatementInterest.Status.INTERESTED,
                ).exists()

        detail_data = ProblemStatementDetailSerializer(
            ps, context={'request': request}
        ).data
        detail_data['viewer_interested'] = viewer_interested

        return CustomResponse(
            general_message="Problem Statement detail retrieved.",
            response=detail_data,
        ).get_success_response()


class ProblemStatementInterestAPI(APIView):
    """
    POST   /api/v1/dashboard/problem-statements/<ps_id>/interest/ → Express interest
    PATCH  /api/v1/dashboard/problem-statements/<ps_id>/interest/ → Edit work link / note
    DELETE /api/v1/dashboard/problem-statements/<ps_id>/interest/ → Withdraw interest
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Problem Statement'],
        description="Register learner interest in a published problem statement before deadline.",
    )
    def post(self, request, ps_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        if not _is_learner_role(roles):
            return CustomResponse(
                general_message="Company accounts cannot register interest in Problem Statements."
            ).get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

        serializer = ProblemStatementInterestSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        note = serializer.validated_data.get('note')
        work_link = serializer.validated_data.get('work_link')

        with transaction.atomic():
            ps_locked = ProblemStatement.objects.select_for_update().filter(
                id=ps_id, deleted_at__isnull=True
            ).first()

            if not ps_locked:
                return CustomResponse(
                    general_message="Problem Statement not found."
                ).get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)

            if ps_locked.status != ProblemStatement.Status.PUBLISHED:
                return CustomResponse(
                    general_message=f"Problem Statement is not open for interest (status: {ps_locked.status})."
                ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

            now = timezone.now()
            if ps_locked.deadline and ps_locked.deadline <= now:
                return CustomResponse(
                    general_message="The deadline to register interest for this Problem Statement has passed."
                ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

            existing_interest = ProblemStatementInterest.objects.filter(
                problem_statement=ps_locked, user_id=user_id
            ).first()

            if existing_interest:
                if existing_interest.status == ProblemStatementInterest.Status.INTERESTED:
                    return CustomResponse(
                        general_message="You have already registered interest for this Problem Statement."
                    ).get_failure_response(status_code=409, http_status_code=status.HTTP_409_CONFLICT)

                # Reactivate withdrawn interest
                existing_interest.status = ProblemStatementInterest.Status.INTERESTED
                if note is not None:
                    existing_interest.note = note
                if work_link is not None:
                    existing_interest.work_link = work_link
                existing_interest.status_updated_by_id = user_id
                existing_interest.save()
                interest = existing_interest
            else:
                # Create new interest record
                interest = ProblemStatementInterest.objects.create(
                    id=str(uuid.uuid4()),
                    problem_statement=ps_locked,
                    user_id=user_id,
                    status=ProblemStatementInterest.Status.INTERESTED,
                    note=note,
                    work_link=work_link,
                    status_updated_by_id=user_id,
                )

            # Sync counter
            active_count = ProblemStatementInterest.objects.filter(
                problem_statement=ps_locked,
                status=ProblemStatementInterest.Status.INTERESTED,
            ).count()
            ps_locked.interest_count = active_count
            ps_locked.save(update_fields=['interest_count'])

        return CustomResponse(
            general_message="Interest registered successfully.",
            response=ProblemStatementInterestSerializer(interest).data,
        ).get_success_response()

    @extend_schema(
        tags=['Problem Statement'],
        description="Modify work_link or note on an active interest before deadline.",
    )
    def patch(self, request, ps_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        if not _is_learner_role(roles):
            return CustomResponse(
                general_message="Company accounts cannot manage interest in Problem Statements."
            ).get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            ps_locked = ProblemStatement.objects.select_for_update().filter(
                id=ps_id, deleted_at__isnull=True
            ).first()

            if not ps_locked:
                return CustomResponse(
                    general_message="Problem Statement not found."
                ).get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)

            if ps_locked.status != ProblemStatement.Status.PUBLISHED:
                return CustomResponse(
                    general_message=f"Problem Statement is not open for interest modification (status: {ps_locked.status})."
                ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

            now = timezone.now()
            if ps_locked.deadline and ps_locked.deadline <= now:
                return CustomResponse(
                    general_message="The deadline to modify interest details has passed."
                ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

            interest = ProblemStatementInterest.objects.filter(
                problem_statement=ps_locked,
                user_id=user_id,
                status=ProblemStatementInterest.Status.INTERESTED,
            ).first()

            if not interest:
                return CustomResponse(
                    general_message="No active interest registration found to modify."
                ).get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)

            serializer = ProblemStatementInterestSerializer(
                interest, data=request.data, partial=True
            )
            if not serializer.is_valid():
                return CustomResponse(
                    general_message=serializer.errors
                ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

            serializer.save()

        return CustomResponse(
            general_message="Interest updated successfully.",
            response=ProblemStatementInterestSerializer(interest).data,
        ).get_success_response()

    @extend_schema(
        tags=['Problem Statement'],
        description="Withdraw registered interest in a problem statement and update interest counter.",
    )
    def delete(self, request, ps_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        if not _is_learner_role(roles):
            return CustomResponse(
                general_message="Company accounts cannot manage interest in Problem Statements."
            ).get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            ps_locked = ProblemStatement.objects.select_for_update().filter(
                id=ps_id, deleted_at__isnull=True
            ).first()

            if not ps_locked:
                return CustomResponse(
                    general_message="Problem Statement not found."
                ).get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)

            interest = ProblemStatementInterest.objects.filter(
                problem_statement=ps_locked,
                user_id=user_id,
                status=ProblemStatementInterest.Status.INTERESTED,
            ).first()

            if not interest:
                return CustomResponse(
                    general_message="No active interest registration found to withdraw."
                ).get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)

            interest.status = ProblemStatementInterest.Status.WITHDRAWN
            interest.status_updated_by_id = user_id
            interest.save(update_fields=['status', 'status_updated_by', 'status_updated_at', 'updated_at'])

            active_count = ProblemStatementInterest.objects.filter(
                problem_statement=ps_locked,
                status=ProblemStatementInterest.Status.INTERESTED,
            ).count()
            ps_locked.interest_count = max(0, active_count)
            ps_locked.save(update_fields=['interest_count'])

        return CustomResponse(
            general_message="Interest withdrawn successfully.",
            response={'id': interest.id, 'status': ProblemStatementInterest.Status.WITHDRAWN},
        ).get_success_response()


class LearnerMyInterestsAPI(APIView):
    """
    GET /api/v1/dashboard/problem-statements/my-interests/
    Returns paginated list of problem statements where the authenticated learner has active interest.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Problem Statement'],
        description="Retrieve a paginated list of problem statements where the authenticated learner has active interest.",
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        if not _is_learner_role(roles):
            return CustomResponse(
                general_message="Company accounts do not have a learner interests feed."
            ).get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

        interests = ProblemStatementInterest.objects.filter(
            user_id=user_id,
            status=ProblemStatementInterest.Status.INTERESTED,
            problem_statement__deleted_at__isnull=True,
        ).select_related('problem_statement', 'problem_statement__company')

        paginated = CommonUtils.get_paginated_queryset(
            interests,
            request,
            search_fields=['problem_statement__title', 'problem_statement__summary'],
            sort_fields={'expressed_at': 'expressed_at', 'created_at': 'created_at'},
        )

        serialized_data = []
        for interest in paginated['queryset']:
            ps_data = ProblemStatementListItemSerializer(
                interest.problem_statement, context={'request': request}
            ).data
            ps_data['viewer_interested'] = True
            ps_data['my_interest'] = ProblemStatementInterestSerializer(interest).data
            serialized_data.append(ps_data)

        return CustomResponse().paginated_response(
            data=serialized_data,
            pagination=paginated['pagination'],
        )
