from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from db.company import Company, CompanyJob, CompanyJobApplication
from db.user import User, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from .application_serializers import (
    ApplicationCreateSerializer,
    ApplicationStatusUpdateSerializer,
    ApplicantDetailSerializer,
    LearnerApplicationListSerializer,
)
from .jobs_views import BaseCompanyJobView
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s


# ---------------------------------------------------------------------------
# Shared auth helpers
# ---------------------------------------------------------------------------

def _get_user(request):
    """Return the User from the JWT, or None on failure."""
    try:
        user_id = JWTUtils.fetch_user_id(request)
    except Exception:
        return None
    return User.objects.filter(id=user_id).first()


def _is_company_role(user):
    """True if the user holds the Company role."""
    return UserRoleLink.objects.filter(
        user=user,
        role__title=RoleType.COMPANY.value,
    ).exists()


def _unauthorized(msg, code):
    return CustomResponse(
        general_message=msg,
        message={"error_code": code},
    ).get_failure_response(
        status_code=401,
        http_status_code=status.HTTP_401_UNAUTHORIZED,
    )


def _forbidden(msg, code):
    return CustomResponse(
        general_message=msg,
        message={"error_code": code},
    ).get_failure_response(
        status_code=403,
        http_status_code=status.HTTP_403_FORBIDDEN,
    )


def _not_found(msg, code):
    return CustomResponse(
        general_message=msg,
        message={"error_code": code},
    ).get_failure_response(
        status_code=404,
        http_status_code=status.HTTP_404_NOT_FOUND,
    )


def _bad_request(msg, code, extra=None):
    message = {"error_code": code}
    if extra:
        message.update(extra)
    return CustomResponse(
        general_message=msg,
        message=message,
    ).get_failure_response(
        status_code=400,
        http_status_code=status.HTTP_400_BAD_REQUEST,
    )


def _server_error():
    return CustomResponse(
        general_message="Something went wrong.",
        message={"error_code": "SERVER_ERROR"},
    ).get_failure_response(
        status_code=500,
        http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ---------------------------------------------------------------------------
# Learner: Apply to a job
# ---------------------------------------------------------------------------

class ApplyToJobAPIView(APIView):
    """
    POST company/jobs/<job_id>/apply/

    Allows any non-company authenticated learner to apply to an active job.

    Body (all optional):
        cover_note  (str, max 1000 chars)

    Prevents:
        - Duplicate applications (one per learner per job)
        - Applications to deleted / closed / draft jobs
        - Company users applying to jobs
    """

    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company - Jobs'],
        description="Create Apply To Job.",
        request=ApplicationCreateSerializer,
        responses={200: ApplicationCreateSerializer},
    )
    def post(self, request, job_id):
        # 1. Authenticate
        user = _get_user(request)
        if not user:
            return _unauthorized("User not found or token invalid.", "USER_NOT_FOUND")

        # 2. Block company users from applying
        if _is_company_role(user):
            return _forbidden(
                "Company users cannot apply to job postings.",
                "COMPANY_CANNOT_APPLY",
            )

        # 3. Fetch the job — must be active and not soft-deleted
        try:
            job = CompanyJob.objects.select_related('company_id').get(
                id=job_id,
                is_deleted=False,
                status='Active',
            )
        except CompanyJob.DoesNotExist:
            return _not_found(
                "Job not found or is no longer active.",
                "JOB_NOT_FOUND",
            )

        # 4. Prevent duplicate application
        if CompanyJobApplication.objects.filter(job=job, applicant=user).exists():
            return _bad_request(
                "You have already applied to this job.",
                "DUPLICATE_APPLICATION",
            )

        # 5. Task-completion gate — block if the job requires a completed task
        if job.requires_task_completion and job.linked_task_id:
            from db.task import KarmaActivityLog
            task_completed = KarmaActivityLog.objects.filter(
                user=user,
                task_id=job.linked_task_id,
                appraiser_approved=True,
            ).exists()
            if not task_completed:
                return _bad_request(
                    "You must complete the required task before applying to this job.",
                    "TASK_NOT_COMPLETED",
                    {"linked_task_id": str(job.linked_task_id)},
                )

        # 6. Validate body
        serializer = ApplicationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _bad_request(
                "Invalid input data.",
                "VALIDATION_ERROR",
                {"errors": serializer.errors},
            )

        # 7. Create application
        application = CompanyJobApplication.objects.create(
            job=job,
            applicant=user,
            status='applied',
            cover_note=serializer.validated_data.get('cover_note') or None,
        )

        return CustomResponse(
            general_message="Application submitted successfully.",
            response={
                "application_id": str(application.id),
                "job_id":         str(job.id),
                "job_title":      job.title,
                "status":         application.status,
                "applied_at":     application.created_at.isoformat(),
            },
        ).get_success_response()


# ---------------------------------------------------------------------------
# Learner: View own applications
# ---------------------------------------------------------------------------

class LearnerApplicationsAPIView(APIView):
    """
    GET company/applications/

    Returns a paginated list of all applications submitted by the authenticated learner.
    Excludes company-role users (they have no applications).

    Sort fields: status, applied_at
    Search fields: job title (via job__title)
    """

    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company - Jobs'],
        description="Retrieve Learner Applications.",
        responses={200: LearnerApplicationListSerializer},
    )
    def get(self, request):
        # 1. Authenticate
        user = _get_user(request)
        if not user:
            return _unauthorized("User not found or token invalid.", "USER_NOT_FOUND")

        # 2. Block company users
        if _is_company_role(user):
            return _forbidden(
                "Company users do not have applications.",
                "COMPANY_ROLE_NOT_ALLOWED",
            )

        # 3. Build queryset
        try:
            queryset = (
                CompanyJobApplication.objects
                .filter(applicant=user)
                .select_related('job__company_id')
                .order_by('-created_at')
            )

            paginated_data = CommonUtils.get_paginated_queryset(
                queryset=queryset,
                request=request,
                search_fields=["job__title", "status"],
                sort_fields={
                    "appliedAt": "created_at",
                    "status":    "status",
                },
                is_pagination=True,
            )
        except Exception:
            return _server_error()

        serializer = LearnerApplicationListSerializer(
            list(paginated_data["queryset"]), many=True
        )

        return CustomResponse(
            general_message="Applications fetched successfully.",
            response={
                "applications": serializer.data,
                "pagination":   paginated_data["pagination"],
            },
        ).get_success_response()


# ---------------------------------------------------------------------------
# Company: List applicants for a job
# ---------------------------------------------------------------------------

class CompanyJobApplicationsListAPIView(BaseCompanyJobView):
    """
    GET company/jobs/<job_id>/applications/

    Returns a paginated list of all applicants for a specific job,
    visible only to the company that owns the job.

    Optional filter:  ?status=applied|shortlisted|accepted|rejected|withdrawn
    Sort fields:      karma, appliedAt, name
    """

    @extend_schema(
        tags=['Dashboard - Company - Jobs'],
        description="Retrieve Company Job Applications List.",
        responses={200: ApplicantDetailSerializer},
    )
    def get(self, request, job_id):
        # 1. Authenticate
        user = self.get_authenticated_user(request)
        if not user:
            return _unauthorized("User not found or token invalid.", "USER_NOT_FOUND")

        # 2. Fetch job
        try:
            job = CompanyJob.objects.get(id=job_id, is_deleted=False)
        except CompanyJob.DoesNotExist:
            return _not_found("Job not found.", "JOB_NOT_FOUND")

        # 3. Authorise — caller must own the company that posted this job
        authorized, _company, error_response = self.check_company_authorization(user, job=job)
        if not authorized:
            return error_response

        # 4. Build queryset
        try:
            queryset = (
                CompanyJobApplication.objects
                .filter(job=job)
                .select_related(
                    'applicant',
                    'applicant__district',
                    'applicant__wallet_user',
                    'applicant__user_lvl_link_user__level',
                    'reviewed_by',
                )
                .order_by('-created_at')
            )

            # Optional status filter
            status_filter = request.query_params.get('status')
            if status_filter:
                valid_statuses = [s[0] for s in CompanyJobApplication.STATUS_CHOICES]
                if status_filter not in valid_statuses:
                    return _bad_request(
                        f"Invalid status filter. Valid values: {valid_statuses}",
                        "INVALID_STATUS_FILTER",
                    )
                queryset = queryset.filter(status=status_filter)

            paginated_data = CommonUtils.get_paginated_queryset(
                queryset=queryset,
                request=request,
                search_fields=["applicant__full_name", "applicant__muid", "status"],
                sort_fields={
                    "karma":     "applicant__wallet_user__karma",
                    "appliedAt": "created_at",
                    "name":      "applicant__full_name",
                },
                is_pagination=True,
            )
        except Exception:
            return _server_error()

        serializer = ApplicantDetailSerializer(
            list(paginated_data["queryset"]), many=True
        )

        return CustomResponse(
            general_message="Applicants fetched successfully.",
            response={
                "job_id":      str(job.id),
                "job_title":   job.title,
                "applicants":  serializer.data,
                "pagination":  paginated_data["pagination"],
            },
        ).get_success_response()


# ---------------------------------------------------------------------------
# Company: Update application status (shortlist / accept / reject)
# ---------------------------------------------------------------------------

class CompanyUpdateApplicationStatusAPIView(BaseCompanyJobView):
    """
    PATCH company/jobs/<job_id>/applications/<app_id>/

    Allows the owning company to move an application through the status FSM:
        applied     → shortlisted | rejected
        shortlisted → accepted    | rejected
        accepted    → (terminal, no update allowed)
        rejected    → (terminal, no update allowed)

    Body (required):
        status  (str)  — one of the values in CompanyJobApplication.STATUS_CHOICES
    """

    @extend_schema(
        tags=['Dashboard - Company - Jobs'],
        description="Partially update Company Update Application Status.",
        request=ApplicationStatusUpdateSerializer,
        responses={200: ApplicationStatusUpdateSerializer},
    )
    def patch(self, request, job_id, app_id):
        # 1. Authenticate
        user = self.get_authenticated_user(request)
        if not user:
            return _unauthorized("User not found or token invalid.", "USER_NOT_FOUND")

        # 2. Fetch job
        try:
            job = CompanyJob.objects.get(id=job_id, is_deleted=False)
        except CompanyJob.DoesNotExist:
            return _not_found("Job not found.", "JOB_NOT_FOUND")

        # 3. Authorise
        authorized, _company, error_response = self.check_company_authorization(user, job=job)
        if not authorized:
            return error_response

        # 4. Fetch application
        try:
            application = CompanyJobApplication.objects.select_related('applicant').get(
                id=app_id,
                job=job,
            )
        except CompanyJobApplication.DoesNotExist:
            return _not_found(
                "Application not found for this job.",
                "APPLICATION_NOT_FOUND",
            )

        # 5. Validate transition (FSM enforced by serializer)
        serializer = ApplicationStatusUpdateSerializer(
            data=request.data,
            context={'current_status': application.status},
        )
        if not serializer.is_valid():
            return _bad_request(
                "Invalid status transition.",
                "INVALID_TRANSITION",
                {"errors": serializer.errors},
            )

        # 6. Apply the status change
        new_status = serializer.validated_data['status']
        application.status      = new_status
        application.reviewed_by = user
        application.reviewed_at = timezone.now()
        application.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])

        return CustomResponse(
            general_message=f"Application {new_status} successfully.",
            response={
                "application_id": str(application.id),
                "applicant_id":   str(application.applicant.id),
                "new_status":     application.status,
                "reviewed_by":    str(user.id),
                "reviewed_at":    application.reviewed_at.isoformat(),
            },
        ).get_success_response()


# ---------------------------------------------------------------------------
# Learner: Withdraw own application
# ---------------------------------------------------------------------------

class LearnerWithdrawApplicationAPIView(APIView):
    """
    PATCH company/applications/<app_id>/withdraw/

    Allows the authenticated learner to withdraw their own application,
    as long as it is still in 'applied' or 'shortlisted' status.
    Terminal statuses (accepted, rejected, withdrawn) cannot be changed.
    """

    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Company - Jobs'], description="Partially update Learner Withdraw Application.",
        responses={200: inline_serializer(
            name='ApplicationLearnerWithdrawResponse',
            fields={
                'application_id': s.CharField(),
                'job_id': s.CharField(),
                'new_status': s.CharField(),
            },
        )},
    )
    def patch(self, request, app_id):
        # 1. Authenticate
        user = _get_user(request)
        if not user:
            return _unauthorized("User not found or token invalid.", "USER_NOT_FOUND")

        # 2. Block company users
        if _is_company_role(user):
            return _forbidden(
                "Company users cannot withdraw applications.",
                "COMPANY_ROLE_NOT_ALLOWED",
            )

        # 3. Fetch the application — must belong to this user
        try:
            application = CompanyJobApplication.objects.select_related('job').get(
                id=app_id,
                applicant=user,
            )
        except CompanyJobApplication.DoesNotExist:
            return _not_found(
                "Application not found.",
                "APPLICATION_NOT_FOUND",
            )

        # 4. Enforce FSM: only applied / shortlisted can be withdrawn
        if application.status not in ('applied', 'shortlisted'):
            return _bad_request(
                f"Cannot withdraw an application with status '{application.status}'.",
                "INVALID_STATUS_TRANSITION",
            )

        # 5. Apply the withdrawal
        application.status = 'withdrawn'
        application.save(update_fields=['status', 'updated_at'])

        return CustomResponse(
            general_message="Application withdrawn successfully.",
            response={
                "application_id": str(application.id),
                "job_id":         str(application.job.id),
                "new_status":     application.status,
            },
        ).get_success_response()
