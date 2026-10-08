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
from utils import problem_statement as ps_utils
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from . import serializers

COMPANY = ["Dashboard - Problem Statements (Company)"]
ADMIN = ["Dashboard - Problem Statements (Admin)"]

SORT_FIELDS = {
    "title": "title",
    "created_at": "created_at",
    "updated_at": "updated_at",
    "published_at": "published_at",
    "deadline": "deadline",
}


def role_guarded(roles):
    """Class decorator: wraps every HTTP handler of the view in ``role_required(roles)``."""
    def decorator(cls):
        for method in ("get", "post", "patch", "delete"):
            handler = getattr(cls, method, None)
            if handler:
                setattr(cls, method, role_required(roles)(handler))
        return cls
    return decorator


def company_scope(request):
    """
    (queryset, company, error). The Company role is enforced by ``role_required``;
    this adds ownership: the verified company registered by the caller. Co-admins
    and company mentors are not accepted.
    """
    company = Company.objects.filter(
        company_user_id=JWTUtils.fetch_user_id(request), status="verified"
    ).first()
    if not company:
        return None, None, ps_utils.failure("Verified company profile not found or access denied.", 403)
    return ps_utils.statement_queryset().filter(company=company), company, None


def admin_scope(request):
    """(queryset, company, error) for an admin (role enforced by ``role_required``): every statement."""
    return ps_utils.statement_queryset(), None, None


class ManageBase(APIView):
    permission_classes = [CustomizePermission]
    scope_fn = None  # set by subclasses

    def scope(self, request):
        return type(self).scope_fn(request)

    def render(self, statements, many=False):
        items = list(statements) if many else [statements]
        ctx = {"counts": ps_utils.interaction_counts([s.id for s in items]), "show_audit": True}
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
            return None, ps_utils.not_found()
        return statement, None

    def fresh(self, statement_id):
        """Re-read after a locked write so the response shows the stored values."""
        return ps_utils.statement_queryset().filter(id=statement_id).first()


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
        return CustomResponse().paginated_response(
            data=self.render(page["queryset"], many=True), pagination=page["pagination"]
        )

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
                return ps_utils.failure("Company not found.", 404)
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
        statement = self.fresh(statement.id)
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
        error = ps_utils.apply_changes(
            statement.id, serializer.validated_data, JWTUtils.fetch_user_id(request)
        )
        if error:
            return error
        return CustomResponse(
            general_message="Problem statement updated.", response=self.render(self.fresh(statement.id))
        ).get_success_response()

    def delete(self, request, statement_id):
        statement, error = self.find(request, statement_id)
        if error:
            return error
        statement.delete()  # interactions go with it via the FK cascade
        return CustomResponse(general_message="Problem statement deleted.").get_success_response()


class StatusActionBase(ManageBase):
    mutation = None  # ps_utils.publish / ps_utils.unpublish
    message = ""

    def post(self, request, statement_id):
        statement, error = self.find(request, statement_id)
        if error:
            return error
        error = type(self).mutation(statement.id, JWTUtils.fetch_user_id(request))
        if error:
            return error
        return CustomResponse(
            general_message=self.message, response=self.render(self.fresh(statement.id))
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
        counts = ps_utils.interaction_counts([statement.id]).get(statement.id, {})
        return CustomResponse(response={
            "counts": {s: counts.get(s, 0) for s in ProblemStatementInteraction.Status.values},
        }).paginated_response(data=users, pagination=page["pagination"])


# --------------------------------------------------------------------------- company

@extend_schema_view(
    get=extend_schema(tags=COMPANY, description="List the company's own problem statements."),
    post=extend_schema(tags=COMPANY, description="Create a problem statement (saved as Draft).",
                       request=serializers.ProblemStatementWriteSerializer),
)
@role_guarded([RoleType.COMPANY.value])
class CompanyProblemStatementListAPI(ListCreateBase):
    scope_fn = staticmethod(company_scope)


@extend_schema_view(
    get=extend_schema(tags=COMPANY),
    delete=extend_schema(tags=COMPANY),
    patch=extend_schema(tags=COMPANY, request=serializers.ProblemStatementWriteSerializer),
)
@role_guarded([RoleType.COMPANY.value])
class CompanyProblemStatementDetailAPI(DetailBase):
    scope_fn = staticmethod(company_scope)


@extend_schema_view(post=extend_schema(tags=COMPANY, description="Publish a problem statement.", request=None))
@role_guarded([RoleType.COMPANY.value])
class CompanyProblemStatementPublishAPI(StatusActionBase):
    scope_fn = staticmethod(company_scope)
    mutation = staticmethod(ps_utils.publish)
    message = "Problem statement published."


@extend_schema_view(post=extend_schema(tags=COMPANY, description="Unpublish a problem statement.", request=None))
@role_guarded([RoleType.COMPANY.value])
class CompanyProblemStatementUnpublishAPI(StatusActionBase):
    scope_fn = staticmethod(company_scope)
    mutation = staticmethod(ps_utils.unpublish)
    message = "Problem statement unpublished."


@extend_schema_view(get=extend_schema(tags=COMPANY, description="Interaction counts and users."))
@role_guarded([RoleType.COMPANY.value])
class CompanyProblemStatementInteractionsAPI(InteractionsBase):
    scope_fn = staticmethod(company_scope)


# --------------------------------------------------------------------------- admin

@extend_schema_view(
    get=extend_schema(tags=ADMIN, description="List problem statements of all companies."),
    post=extend_schema(tags=ADMIN, description="Create a problem statement for any company.",
                       request=serializers.AdminProblemStatementCreateSerializer),
)
@role_guarded([RoleType.ADMIN.value])
class AdminProblemStatementListAPI(ListCreateBase):
    scope_fn = staticmethod(admin_scope)


@extend_schema_view(
    get=extend_schema(tags=ADMIN),
    delete=extend_schema(tags=ADMIN),
    patch=extend_schema(tags=ADMIN, request=serializers.ProblemStatementWriteSerializer),
)
@role_guarded([RoleType.ADMIN.value])
class AdminProblemStatementDetailAPI(DetailBase):
    scope_fn = staticmethod(admin_scope)


@extend_schema_view(post=extend_schema(tags=ADMIN, request=None))
@role_guarded([RoleType.ADMIN.value])
class AdminProblemStatementPublishAPI(StatusActionBase):
    scope_fn = staticmethod(admin_scope)
    mutation = staticmethod(ps_utils.publish)
    message = "Problem statement published."


@extend_schema_view(post=extend_schema(tags=ADMIN, request=None))
@role_guarded([RoleType.ADMIN.value])
class AdminProblemStatementUnpublishAPI(StatusActionBase):
    scope_fn = staticmethod(admin_scope)
    mutation = staticmethod(ps_utils.unpublish)
    message = "Problem statement unpublished."


@extend_schema_view(get=extend_schema(tags=ADMIN))
@role_guarded([RoleType.ADMIN.value])
class AdminProblemStatementInteractionsAPI(InteractionsBase):
    scope_fn = staticmethod(admin_scope)


class AdminProblemStatementInteractionDetailAPI(ManageBase):
    scope_fn = staticmethod(admin_scope)

    @extend_schema(tags=ADMIN, description="Remove a user's interaction from a problem statement.")
    @role_required([RoleType.ADMIN.value])
    def delete(self, request, statement_id, user_id):
        statement, error = self.find(request, statement_id)
        if error:
            return error
        deleted, _ = ProblemStatementInteraction.objects.filter(
            problem_statement=statement, user_id=user_id
        ).delete()
        if not deleted:
            return ps_utils.failure("Interaction not found.", 404)
        return CustomResponse(general_message="Interaction removed.").get_success_response()
