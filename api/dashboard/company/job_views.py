from utils.utils import DateTimeUtils
from rest_framework.views import APIView
from django.db.models import Q, F
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils, DateTimeUtils
from db.job import CompanyJob, UserJobApplication
from db.company import Company, CompanyAdminLink
from db.user import User
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from api.notification.notifications_utils import NotificationUtils
from django.conf import settings
from . import job_serializers
from .company_views import _get_company_for_user

# Addon §6.4 — rate/abuse limit: cap how many drafts-pending-approval a
# single mentor can have open at once, so an active grant can't be used to
# spam postings before an owner catches it.
MAX_PENDING_JOBS_PER_MENTOR = 5


def _is_company_owner(user_id, company):
    from .company_views import is_company_owner_or_admin
    return is_company_owner_or_admin(user_id, company)


class CompanyJobAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description=(
            "Post a new job/gig. "
            "Jobs are always created with status='Draft' regardless of any status value sent in the request body. "
            "Use PATCH /jobs/{job_id}/ to change the status to 'Pending Approval', then the company owner "
            "approves via /jobs/{job_id}/approve/ to make it 'Active'. Owner-created jobs may set 'Active' directly."
        ),
        request=job_serializers.JobCreateSerializer,
        responses={200: job_serializers.JobCreateSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company:
            return CustomResponse(
                general_message="Verified company profile not found or access denied."
            ).get_failure_response(status_code=403)

        # An owner or an accepted delegate can post/approve jobs.
        is_owner_or_delegate = company.company_user_id == user_id
        if not is_owner_or_delegate:
            is_owner_or_delegate = CompanyAdminLink.objects.filter(
                company=company,
                user_id=user_id,
                status='Accepted'
            ).exists()

        # A deactivated company mentor cannot post jobs on the company's
        # behalf (owners/delegates aren't gated by mentor-active status).
        if not is_owner_or_delegate:
            from db.user import UserMentor
            mentor_profile = UserMentor.objects.filter(user_id=user_id).first()
            if not mentor_profile or not mentor_profile.is_active:
                return CustomResponse(
                    general_message="Your mentor account is deactivated. Please contact an administrator."
                ).get_failure_response(status_code=403)

            # Addon §6.4 — cap how many drafts-pending-approval this mentor
            # can have open at once.
            pending_count = CompanyJob.objects.filter(
                company=company, created_by_id=user_id, is_deleted=False,
                status__in=[CompanyJob.Status.PENDING_APPROVAL, CompanyJob.Status.NEEDS_REVISION],
            ).count()
            if pending_count >= MAX_PENDING_JOBS_PER_MENTOR:
                return CustomResponse(
                    general_message=f"You already have {MAX_PENDING_JOBS_PER_MENTOR} pending/needs-revision job postings. Resolve those before submitting more."
                ).get_failure_response(status_code=429)

        serializer = job_serializers.JobCreateSerializer(
            data=request.data, context={"user_id": user_id, "company": company, "is_owner": is_owner_or_delegate}
        )
        if serializer.is_valid():
            job = serializer.save()
            if is_owner_or_delegate:
                message = "Job posted successfully."
            else:
                message = "Job submitted for approval successfully."
                # Notify company owner
                try:
                    from api.notification.notifications_utils import NotificationUtils
                    from django.conf import settings

                    mentor = User.objects.get(id=user_id)
                    owner = company.company_user

                    NotificationUtils.insert_notification(
                        user=owner,
                        title="New Job Posting for Approval",
                        description=f"Mentor {mentor.full_name} has submitted a new job posting '{job.title}' for your approval.",
                        button="View Jobs",
                        url=f"{settings.FR_DOMAIN_NAME}/dashboard/company/jobs/pending/",
                        created_by=mentor,
                    )
                except Exception:
                    # Silently fail on notification error
                    pass

            return CustomResponse(
                general_message=message,
                response=serializer.data
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="List all jobs for the authenticated company (creator or company mentor).",
        responses={200: job_serializers.JobListSerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company:
            return CustomResponse(general_message="Company profile not found or access denied.").get_failure_response(
                status_code=404)

        is_owner_or_delegate = company.company_user_id == user_id
        if not is_owner_or_delegate:
            is_owner_or_delegate = CompanyAdminLink.objects.filter(
                company=company,
                user_id=user_id,
                status='Accepted'
            ).exists()

        if is_owner_or_delegate:
            jobs = CompanyJob.objects.filter(company=company, is_deleted=False)
        else:  # Mentor
            jobs = CompanyJob.objects.filter(
                Q(company=company, is_deleted=False, status='Active') |
                Q(company=company, is_deleted=False, created_by_id=user_id)
            ).distinct()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            jobs, request,
            search_fields=["title", "location", "job_type"],
            sort_fields={"title": "title", "created_at": "created_at"}
        )
        serializer = job_serializers.JobListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class CompanyJobDetailAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="Retrieve details of a specific job.",
        responses={200: job_serializers.JobListSerializer},
    )
    def get(self, request, job_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        job = CompanyJob.objects.filter(id=job_id, company=company, is_deleted=False).first()
        if not job:
            return CustomResponse(general_message="Job not found or access denied.").get_failure_response(status_code=404)
        serializer = job_serializers.JobListSerializer(job)
        return CustomResponse(response=serializer.data).get_success_response()

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="Update a specific job.",
        request=job_serializers.JobUpdateSerializer,
        responses={200: job_serializers.JobUpdateSerializer},
    )
    def patch(self, request, job_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        job = CompanyJob.objects.filter(id=job_id, company=company, is_deleted=False).first()
        if not job:
            return CustomResponse(general_message="Job not found or access denied.").get_failure_response(status_code=404)

        # Rejected jobs are permanently locked — create a new posting instead.
        if job.status == CompanyJob.Status.REJECTED:
            return CustomResponse(
                general_message="A rejected job cannot be edited. Create a new posting instead."
            ).get_failure_response(status_code=403)

        data = request.data.copy()
        requested_status = data.get('status')

        # A job in Needs Revision going back to Active/Pending Approval = resubmit.
        # Force it through Pending Approval regardless of who is patching.
        if (
            job.status == CompanyJob.Status.NEEDS_REVISION
            and requested_status in (CompanyJob.Status.ACTIVE, CompanyJob.Status.PENDING_APPROVAL)
        ):
            data['status'] = CompanyJob.Status.PENDING_APPROVAL

        if requested_status == CompanyJob.Status.ACTIVE and not _is_company_owner(user_id, company):
            # Job publish gate (§3.1): only the owner may flip a job straight
            # to Active. A non-owner mentor should submit for approval
            # instead — swap the requested transition to Pending Approval.
            data['status'] = CompanyJob.Status.PENDING_APPROVAL

        # The owner's approval only covers the content that existed at
        # approval time — a non-owner mentor editing the content of an
        # already-Active job must go back through review rather than
        # silently publishing the edit under the prior approval.
        non_status_fields = set(data.keys()) - {'status'}
        if (
            job.status == CompanyJob.Status.ACTIVE
            and non_status_fields
            and not _is_company_owner(user_id, company)
        ):
            data['status'] = CompanyJob.Status.PENDING_APPROVAL

        needs_reapproval = data.get('status') == CompanyJob.Status.PENDING_APPROVAL and not _is_company_owner(user_id, company)

        serializer = job_serializers.JobUpdateSerializer(job, data=data, partial=True, context={'user_id': user_id})
        if serializer.is_valid():
            serializer.save()
            general_message = "Job updated successfully."
            if needs_reapproval:
                general_message = "Job submitted for owner approval (only the company owner can publish directly)."
                try:
                    from api.notification.notifications_utils import NotificationUtils
                    from db.user import User
                    actor = User.every.filter(id=user_id).first()
                    NotificationUtils.insert_notification(
                        user=company.company_user,
                        title="Job Posting Awaiting Approval",
                        description=f'A job "{job.title}" is awaiting your approval.',
                        button="Review",
                        url=None,
                        created_by=actor,
                    )
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception("Failed to notify company owner of job %s awaiting approval", job.id)
            return CustomResponse(
                general_message=general_message,
                response=serializer.data
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="Delete a specific job.",
    )
    def delete(self, request, job_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        job = CompanyJob.objects.filter(id=job_id, company=company, is_deleted=False).first()
        if not job:
            return CustomResponse(general_message="Job not found or access denied.").get_failure_response(status_code=404)
        job.is_deleted = True
        job.updated_at = DateTimeUtils.get_current_utc_time()
        job.updated_by_id = user_id
        job.save(update_fields=['is_deleted', 'updated_at', 'updated_by'])
        return CustomResponse(general_message="Job deleted successfully.").get_success_response()


class CompanyPendingJobListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="List all jobs pending approval for the authenticated company owner.",
        responses={200: job_serializers.JobListSerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company:
            return CustomResponse(general_message="Company profile not found or access denied.").get_failure_response(
                status_code=404)

        is_owner_or_delegate = company.company_user_id == user_id
        if not is_owner_or_delegate:
            is_owner_or_delegate = CompanyAdminLink.objects.filter(
                company=company, user_id=user_id, status='Accepted'
            ).exists()

        if not is_owner_or_delegate:
            return CustomResponse(general_message="You are not authorized to view pending jobs.").get_failure_response(
                status_code=403)

        jobs = CompanyJob.objects.filter(company=company, status='Pending Approval', is_deleted=False)
        paginated_queryset = CommonUtils.get_paginated_queryset(
            jobs, request,
            search_fields=["title", "location", "job_type", "created_by__full_name"],
            sort_fields={"title": "title", "created_at": "created_at"}
        )
        serializer = job_serializers.JobListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class CompanyJobApproveAPI(APIView):
    """Owner or accepted delegate: approve a job pending approval, publishing it (Active)."""
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Company Jobs'], description="Approve a job posting (owner or delegate only).")
    def post(self, request, job_id):
        from django.db import transaction

        user_id = JWTUtils.fetch_user_id(request)

        with transaction.atomic():
            job = CompanyJob.objects.select_for_update().filter(
                id=job_id, is_deleted=False, company__status="verified"
            ).first()
            if not job:
                return CustomResponse(general_message="Job not found.").get_failure_response(status_code=404)

            if not _is_company_owner(user_id, job.company):
                return CustomResponse(general_message="You are not authorized to approve this job.").get_failure_response(status_code=403)

            if job.created_by_id == user_id:
                return CustomResponse(general_message="You cannot approve your own job posting.").get_failure_response(status_code=403)

            if job.status != CompanyJob.Status.PENDING_APPROVAL:
                return CustomResponse(general_message="Job is not pending approval.").get_failure_response()

            now = DateTimeUtils.get_current_utc_time()
            job.status = CompanyJob.Status.ACTIVE
            job.approved_by_id = user_id
            job.approved_at = now
            job.updated_at = now
            job.updated_by_id = user_id
            job.save(update_fields=["status", "approved_by_id", "approved_at", "updated_at", "updated_by_id"])

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            actor = User.every.filter(id=user_id).first()
            if job.created_by and actor:
                NotificationUtils.insert_notification(
                    user=job.created_by,
                    title="Job Posting Approved",
                    description=f'Your job posting "{job.title}" has been approved and is now live.',
                    button=None, url=None, created_by=actor,
                )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to notify mentor of job %s approval", job.id)

        return CustomResponse(general_message="Job approved and published successfully.").get_success_response()


class CompanyJobRequestChangesAPI(APIView):
    """Owner or accepted delegate: send a job back to the mentor for revision."""
    permission_classes = [CustomizePermission]

    def post(self, request, job_id):
        from django.db import transaction

        user_id = JWTUtils.fetch_user_id(request)

        note = (request.data.get("note") or "").strip()
        if not note:
            return CustomResponse(
                general_message="A revision note is required."
            ).get_failure_response()

        with transaction.atomic():
            job = CompanyJob.objects.select_for_update().filter(
                id=job_id, is_deleted=False,
                status=CompanyJob.Status.PENDING_APPROVAL,
                company__status="verified"
            ).first()
            if not job:
                return CustomResponse(
                    general_message="Job not found or not pending approval."
                ).get_failure_response(status_code=404)

            if not _is_company_owner(user_id, job.company):
                return CustomResponse(
                    general_message="Only the company owner can request changes."
                ).get_failure_response(status_code=403)

            job.status = CompanyJob.Status.NEEDS_REVISION
            job.rejection_reason = note   # reuse this field for the owner's note
            job.updated_by_id = user_id
            job.updated_at = DateTimeUtils.get_current_utc_time()
            job.save(update_fields=["status", "rejection_reason", "updated_at", "updated_by_id"])

        # Notify the mentor
        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            actor = User.every.filter(id=user_id).first()
            if job.created_by and actor:
                NotificationUtils.insert_notification(
                    user=job.created_by,
                    title="Job Posting Needs Revision",
                    description=f'Your job "{job.title}" needs changes: {note}',
                    button=None, url=None, created_by=actor,
                )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to notify mentor of job %s revision request", job.id)
        return CustomResponse(
            general_message="Revision requested. Mentor notified."
        ).get_success_response()


class CompanyJobRejectAPI(APIView):
    """Owner or accepted delegate: reject a job pending approval."""
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Company Jobs'], description="Reject a job posting (owner or delegate only).")
    def post(self, request, job_id):
        from django.db import transaction

        user_id = JWTUtils.fetch_user_id(request)

        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return CustomResponse(general_message="A rejection reason is required.").get_failure_response()

        with transaction.atomic():
            job = CompanyJob.objects.select_for_update().filter(
                id=job_id, is_deleted=False, company__status="verified"
            ).first()
            if not job:
                return CustomResponse(general_message="Job not found.").get_failure_response(status_code=404)

            if not _is_company_owner(user_id, job.company):
                return CustomResponse(general_message="You are not authorized to reject this job.").get_failure_response(status_code=403)

            if job.status != CompanyJob.Status.PENDING_APPROVAL:
                return CustomResponse(general_message="Job is not pending approval.").get_failure_response()

            now = DateTimeUtils.get_current_utc_time()
            job.status = CompanyJob.Status.REJECTED
            job.rejection_reason = reason
            job.updated_at = now
            job.updated_by_id = user_id
            job.save(update_fields=["status", "rejection_reason", "updated_at", "updated_by_id"])

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            actor = User.every.filter(id=user_id).first()
            if job.created_by and actor:
                NotificationUtils.insert_notification(
                    user=job.created_by,
                    title="Job Posting Rejected",
                    description=f'Your job posting "{job.title}" was rejected. Reason: {reason}',
                    button=None, url=None, created_by=actor,
                )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to notify mentor of job %s rejection", job.id)

        return CustomResponse(general_message="Job rejected successfully.").get_success_response()


class PublicJobAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Public - Jobs'],
        description="Public endpoint to list all active jobs.",
        responses={200: job_serializers.JobListSerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        jobs = CompanyJob.objects.filter(status='Active', is_deleted=False, company__status="verified")

        paginated_queryset = CommonUtils.get_paginated_queryset(
            jobs, request,
            search_fields=["title", "location", "job_type", "company__name"],
            sort_fields={"title": "title", "created_at": "created_at"}
        )

        serializer = job_serializers.JobListSerializer(
            paginated_queryset.get("queryset"), many=True, context={"learner_id": user_id}
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class JobApplicationAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="Apply to a job.",
        request=job_serializers.JobApplicationSerializer,
    )
    def post(self, request, job_id):
        user_id = JWTUtils.fetch_user_id(request)

        if User.objects.filter(id=user_id, suspended_at__isnull=False).exists():
            return CustomResponse(general_message="Suspended accounts cannot apply to jobs.").get_failure_response(status_code=403)

        job = CompanyJob.objects.filter(id=job_id, status='Active', is_deleted=False, company__status="verified").first()
        if not job:
            return CustomResponse(general_message="Active job not found.").get_failure_response(status_code=404)

        data = request.data.copy()
        data['job'] = job.id

        serializer = job_serializers.JobApplicationSerializer(
            data=data, context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Application submitted successfully.",
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="List all applications for a specific job (creator or company mentor).",
        responses={200: job_serializers.ApplicationTrackingSerializer(many=True)},
    )
    def get(self, request, job_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        job = CompanyJob.objects.filter(id=job_id, company=company).first()
        if not job:
            return CustomResponse(general_message="Job not found or access denied.").get_failure_response(status_code=404)
        applications = UserJobApplication.objects.filter(job=job)
        paginated_queryset = CommonUtils.get_paginated_queryset(
            applications, request,
            search_fields=["user__full_name", "status"],
            sort_fields={"applied_at": "applied_at", "status": "status"}
        )
        serializer = job_serializers.ApplicationTrackingSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

class ApplicationStatusAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="Update the status of a job application (creator or company mentor).",
        request=job_serializers.ApplicationTrackingSerializer,
        responses={200: job_serializers.ApplicationTrackingSerializer},
    )
    def patch(self, request, app_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        application = UserJobApplication.objects.filter(id=app_id, job__company=company).first()
        if not application:
            return CustomResponse(general_message="Application not found or access denied.").get_failure_response(status_code=404)
        serializer = job_serializers.ApplicationTrackingSerializer(
            application, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Application status updated successfully.",
                response=serializer.data
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

class PublicCompanyJobListAPI(APIView):
    permission_classes = []

    @extend_schema(
        tags=['Public - Company'],
        description="Public endpoint to view all active jobs for a specific company.",
        responses={200: job_serializers.JobListSerializer(many=True)},
    )
    def get(self, request, slug):
        company = Company.objects.filter(slug=slug, status="verified").first()
        if not company:
            return CustomResponse(
                general_message="Company not found."
            ).get_failure_response(status_code=404)

        jobs = CompanyJob.objects.filter(company=company, status='Active', is_deleted=False)
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            jobs, request, 
            search_fields=["title", "location", "job_type"],
            sort_fields={"title": "title", "created_at": "created_at"}
        )
        
        serializer = job_serializers.JobListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

class UserApplicationWithdrawAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="Withdraw a submitted job application.",
    )
    def delete(self, request, app_id):
        user_id = JWTUtils.fetch_user_id(request)

        application = UserJobApplication.objects.filter(id=app_id, user_id=user_id).first()
        if not application:
            return CustomResponse(
                general_message="Application not found or you do not have permission to withdraw it."
            ).get_failure_response(status_code=404)

        if application.status == 'Selected':
            return CustomResponse(
                general_message="A selected application cannot be withdrawn."
            ).get_failure_response(status_code=403)

        # Soft-withdraw rather than hard-delete: preserves the audit trail
        # and stops apply -> withdraw -> re-apply from being usable to erase
        # a Rejected outcome (the row, and the company's history of it,
        # would otherwise vanish). A withdrawn application can be reinstated
        # via the resubmit endpoint, same as a rejected one.
        application.status = 'Withdrawn'
        application.updated_at = DateTimeUtils.get_current_utc_time()
        application.save(update_fields=["status", "updated_at"])

        return CustomResponse(
            general_message="Application withdrawn successfully."
        ).get_success_response()

class UserApplicationResubmitAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="Resubmit a rejected job application.",
        request=job_serializers.UserApplicationResubmitSerializer,
    )
    def patch(self, request, app_id):
        user_id = JWTUtils.fetch_user_id(request)

        application = UserJobApplication.objects.filter(id=app_id, user_id=user_id).first()
        if not application:
            return CustomResponse(
                general_message="Application not found or access denied."
            ).get_failure_response(status_code=404)

        if application.status not in ('Rejected', 'Withdrawn'):
            return CustomResponse(
                general_message="Only rejected or withdrawn applications can be resubmitted."
            ).get_failure_response()

        serializer = job_serializers.UserApplicationResubmitSerializer(
            application, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Application resubmitted successfully.",
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class UserAppliedJobsAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="List all jobs the user has applied to.",
        responses={200: job_serializers.UserAppliedJobsSerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        applications = UserJobApplication.objects.filter(user_id=user_id, job__is_deleted=False)
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            applications, request, 
            search_fields=["job__title", "job__company__name", "status"],
            sort_fields={"applied_at": "applied_at", "status": "status"}
        )
        
        serializer = job_serializers.UserAppliedJobsSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class TrackJobViewAPIView(APIView):
    """
    POST /company/jobs/<job_id>/view/

    Increments the view count for a specific job listing.
    """
    permission_classes = []

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="Increment the view count for a specific job listing.",
    )
    def post(self, request, job_id):
        try:
            # Get the job
            job = CompanyJob.objects.filter(id=job_id, status='Active', is_deleted=False).first()
            if not job:
                return CustomResponse(
                    general_message="Job not found or access denied.",
                    message={"error_code": "JOB_NOT_FOUND"}
                ).get_failure_response(status_code=404)

            # De-duplicate rapid repeat views from the same client so this
            # unauthenticated endpoint can't be trivially scripted to inflate
            # a job's view count (which feeds the company's conversion-rate
            # analytics). One counted view per client per job per hour.
            from django.core.cache import cache
            client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')
            dedup_key = f"job_view_dedup:{job_id}:{client_ip}"
            if not cache.add(dedup_key, True, timeout=3600):
                return CustomResponse(
                    general_message="Job view already tracked recently.",
                    response={}
                ).get_success_response()

            # Increment views
            job.total_views = F('total_views') + 1
            job.save(update_fields=['total_views'])

            return CustomResponse(
                general_message="Job view tracked successfully.",
                response={}
            ).get_success_response()

        except Exception as e:
            return CustomResponse(
                general_message="Something went wrong",
                message={"error_code": "SERVER_ERROR"}
            ).get_failure_response(status_code=500)


class CompanyJobEngagementAnalyticsAPIView(APIView):
    """
    GET /company/jobs/<job_id>/analytics/

    Fetches detailed view, application, and hired statistics for a specific job posting.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="Fetches detailed view, application, and hired statistics for a specific job posting.",
    )
    def get(self, request, job_id):
        try:
            user_id = JWTUtils.fetch_user_id(request)
            company = _get_company_for_user(user_id)
            if not company:
                return CustomResponse(
                    general_message="Company profile not found or access denied."
                ).get_failure_response(status_code=404)

            # Get the job
            job = CompanyJob.objects.filter(id=job_id, company=company, is_deleted=False).first()
            if not job:
                return CustomResponse(
                    general_message="Job not found or access denied.",
                    message={"error_code": "JOB_NOT_FOUND"}
                ).get_failure_response(status_code=404)

            # Aggregate metrics
            total_views = job.total_views
            total_applications = UserJobApplication.objects.filter(job=job).count()
            total_hired = UserJobApplication.objects.filter(job=job, status='Selected').count()

            response_data = {
                "job_id": str(job.id),
                "job_title": job.title,
                "total_views": total_views,
                "total_applications": total_applications,
                "total_hired": total_hired,
                "conversion_rate_percentage": round((total_applications / total_views) * 100, 2) if total_views > 0 else 0.0
            }

            return CustomResponse(
                response=response_data,
                general_message="Job analytics fetched successfully"
            ).get_success_response()

        except Exception as e:
            return CustomResponse(
                general_message="Something went wrong",
                message={"error_code": "SERVER_ERROR"}
            ).get_failure_response(status_code=500)
