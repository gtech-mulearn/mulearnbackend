"""
Company and admin views share one implementation. They differ only in how the
caller's scope is resolved (``company_scope`` / ``admin_scope``), so a company
user can never reach another company's rows: every lookup goes through the
scoped queryset and a miss is a 404.
"""
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.views import APIView

from db.company import Company
from db.problem_statement import ProblemStatement, ProblemStatementInteraction
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils

from . import serializers, services

COMPANY = ["Dashboard - Problem Statements (Company)"]
ADMIN = ["Dashboard - Problem Statements (Admin)"]

SORT_FIELDS = {
    "title": "title",
    "created_at": "created_at",
    "updated_at": "updated_at",
    "published_at": "published_at",
    "deadline": "deadline",
}


class ManageBase(APIView):
    permission_classes = [CustomizePermission]
    scope_fn = None  # set by subclasses

    def scope(self, request):
        return type(self).scope_fn(request)

    def render(self, statements, many=False):
        items = list(statements) if many else [statements]
        ctx = {"counts": services.interaction_counts([s.id for s in items]), "show_audit": True}
        return serializers.ProblemStatementSerializer(
            items if many else statements, many=many, context=ctx
        ).data

    def find(self, request, statement_id):
        """(statement, error): the statement inside the caller's scope, or a 403/404 response."""
        qs, _, error = self.scope(request)
        if error:
            return None, error
        statement = qs.filter(id=statement_id).first()
        if not statement:
            return None, services.failure("Problem statement not found.", 404)
        return statement, None


class ListCreateBase(ManageBase):
    def get(self, request):
        qs, _, error = self.scope(request)
        if error:
            return error
        params = request.query_params
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("category"):
            qs = qs.filter(category__iexact=params["category"])
        if params.get("company_id"):
            qs = qs.filter(company_id=params["company_id"])
        page = CommonUtils.get_paginated_queryset(
            qs.order_by("-updated_at"), request, ["title", "category", "company__name"], SORT_FIELDS
        )
        return CustomResponse(response={
            "data": self.render(page["queryset"], many=True),
            "pagination": page["pagination"],
        }).get_success_response()

    def post(self, request):
        _, company, error = self.scope(request)
        if error:
            return error
        user_id = JWTUtils.fetch_user_id(request)
        serializer_class = (
            serializers.ProblemStatementWriteSerializer
            if company else serializers.AdminProblemStatementCreateSerializer
        )
        serializer = serializer_class(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()
        data = serializer.validated_data
        if company is None:  # admin: the target company comes from the body
            company = Company.objects.filter(id=data["company_id"]).first()
            if not company:
                return services.failure("Company not found.", 404)
        statement = ProblemStatement.objects.create(
            company=company,
            title=data["title"],
            description=data["description"],
            category=data["category"],
            skills=data.get("skills", []),
            deadline=data.get("deadline"),
            status=ProblemStatement.Status.DRAFT,
            created_by_id=user_id,
            updated_by_id=user_id,
        )
        statement = services.statement_queryset().get(id=statement.id)
        return CustomResponse(
            general_message="Problem statement created.", response=self.render(statement)
        ).get_success_response()


class DetailBase(ManageBase):
    def get(self, request, statement_id):
        statement, error = self.find(request, statement_id)
        if error:
            return error
        return CustomResponse(response=self.render(statement)).get_success_response()

    def patch(self, request, statement_id):
        statement, error = self.find(request, statement_id)
        if error:
            return error
        serializer = serializers.ProblemStatementWriteSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()
        services.apply_changes(statement, serializer.validated_data, JWTUtils.fetch_user_id(request))
        return CustomResponse(
            general_message="Problem statement updated.", response=self.render(statement)
        ).get_success_response()

    def delete(self, request, statement_id):
        statement, error = self.find(request, statement_id)
        if error:
            return error
        statement.delete()  # interactions go with it via the FK cascade
        return CustomResponse(general_message="Problem statement deleted.").get_success_response()


class StatusActionBase(ManageBase):
    action = None  # services.publish / services.unpublish
    message = ""

    def post(self, request, statement_id):
        statement, error = self.find(request, statement_id)
        if error:
            return error
        error = type(self).action(statement, JWTUtils.fetch_user_id(request))
        if error:
            return error
        return CustomResponse(
            general_message=self.message, response=self.render(statement)
        ).get_success_response()


class InteractionsBase(ManageBase):
    def get(self, request, statement_id):
        statement, error = self.find(request, statement_id)
        if error:
            return error
        interactions = ProblemStatementInteraction.objects.filter(
            problem_statement=statement
        ).select_related("user")
        page = CommonUtils.get_paginated_queryset(
            interactions, request, ["user__full_name", "user__muid"],
            {"created_at": "created_at", "status": "status", "name": "user__full_name"},
        )
        users = [
            {
                "user_id": i.user_id,
                "muid": i.user.muid,
                "full_name": i.user.full_name,
                "status": i.status,
                "created_at": i.created_at,
                "updated_at": i.updated_at,
            }
            for i in page["queryset"]
        ]
        counts = services.interaction_counts([statement.id]).get(statement.id, {})
        return CustomResponse(response={
            "counts": {s: counts.get(s, 0) for s in ProblemStatementInteraction.Status.values},
            "data": users,
            "pagination": page["pagination"],
        }).get_success_response()


# --------------------------------------------------------------------------- company

@extend_schema_view(
    get=extend_schema(tags=COMPANY, description="List the company's own problem statements."),
    post=extend_schema(tags=COMPANY, description="Create a problem statement (saved as Draft).",
                       request=serializers.ProblemStatementWriteSerializer),
)
class CompanyProblemStatementListAPI(ListCreateBase):
    scope_fn = staticmethod(services.company_scope)


@extend_schema_view(
    get=extend_schema(tags=COMPANY),
    delete=extend_schema(tags=COMPANY),
    patch=extend_schema(tags=COMPANY, request=serializers.ProblemStatementWriteSerializer),
)
class CompanyProblemStatementDetailAPI(DetailBase):
    scope_fn = staticmethod(services.company_scope)


@extend_schema_view(post=extend_schema(tags=COMPANY, description="Publish a problem statement.", request=None))
class CompanyProblemStatementPublishAPI(StatusActionBase):
    scope_fn = staticmethod(services.company_scope)
    action = staticmethod(services.publish)
    message = "Problem statement published."


@extend_schema_view(post=extend_schema(tags=COMPANY, description="Unpublish a problem statement.", request=None))
class CompanyProblemStatementUnpublishAPI(StatusActionBase):
    scope_fn = staticmethod(services.company_scope)
    action = staticmethod(services.unpublish)
    message = "Problem statement unpublished."


@extend_schema_view(get=extend_schema(tags=COMPANY, description="Interaction counts and users."))
class CompanyProblemStatementInteractionsAPI(InteractionsBase):
    scope_fn = staticmethod(services.company_scope)


# --------------------------------------------------------------------------- admin

@extend_schema_view(
    get=extend_schema(tags=ADMIN, description="List problem statements of all companies."),
    post=extend_schema(tags=ADMIN, description="Create a problem statement for any company.",
                       request=serializers.AdminProblemStatementCreateSerializer),
)
class AdminProblemStatementListAPI(ListCreateBase):
    scope_fn = staticmethod(services.admin_scope)


@extend_schema_view(
    get=extend_schema(tags=ADMIN),
    delete=extend_schema(tags=ADMIN),
    patch=extend_schema(tags=ADMIN, request=serializers.ProblemStatementWriteSerializer),
)
class AdminProblemStatementDetailAPI(DetailBase):
    scope_fn = staticmethod(services.admin_scope)


@extend_schema_view(post=extend_schema(tags=ADMIN, request=None))
class AdminProblemStatementPublishAPI(StatusActionBase):
    scope_fn = staticmethod(services.admin_scope)
    action = staticmethod(services.publish)
    message = "Problem statement published."


@extend_schema_view(post=extend_schema(tags=ADMIN, request=None))
class AdminProblemStatementUnpublishAPI(StatusActionBase):
    scope_fn = staticmethod(services.admin_scope)
    action = staticmethod(services.unpublish)
    message = "Problem statement unpublished."


@extend_schema_view(get=extend_schema(tags=ADMIN))
class AdminProblemStatementInteractionsAPI(InteractionsBase):
    scope_fn = staticmethod(services.admin_scope)


class AdminProblemStatementInteractionDetailAPI(ManageBase):
    scope_fn = staticmethod(services.admin_scope)

    @extend_schema(tags=ADMIN, description="Remove a user's interaction from a problem statement.")
    def delete(self, request, statement_id, user_id):
        statement, error = self.find(request, statement_id)
        if error:
            return error
        deleted, _ = ProblemStatementInteraction.objects.filter(
            problem_statement=statement, user_id=user_id
        ).delete()
        if not deleted:
            return services.failure("Interaction not found.", 404)
        return CustomResponse(general_message="Interaction removed.").get_success_response()
