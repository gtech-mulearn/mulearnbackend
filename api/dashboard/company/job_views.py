from utils.utils import DateTimeUtils
from rest_framework.views import APIView
from django.db.models import Q, F
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils
from db.job import CompanyJob, UserJobApplication
from db.company import Company, CompanyAdminLink
from db.user import User
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, inline_serializer
from rest_framework import serializers
from api.notification.notifications_utils import NotificationUtils
from django.conf import settings
from db.mentor import SystemActionLog
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

        data = request.data.copy()
        requested_status = data.get('status')
        if requested_status == CompanyJob.Status.ACTIVE and not _is_company_owner(user_id, company):
            # Job publish gate (§3.1): only the owner may flip a job straight
            # to Active. A non-owner mentor should submit for approval
            # instead — swap the requested transition to Pending Approval.
            data['status'] = CompanyJob.Status.PENDING_APPROVAL

        serializer = job_serializers.JobUpdateSerializer(job, data=data, partial=True, context={'user_id': user_id})
        if serializer.is_valid():
            serializer.save()
            general_message = "Job updated successfully."
            if requested_status == CompanyJob.Status.ACTIVE and not _is_company_owner(user_id, company):
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
                    pass
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


class CompanyJobVerifyAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description="Approve or reject a job posting submitted by a company mentor.",
        request=job_serializers.JobVerifySerializer,
        responses={200: job_serializers.JobListSerializer},
    )
    def patch(self, request, job_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company:
            return CustomResponse(general_message="Company profile not found or access denied.").get_failure_response(
                status_code=403)

        is_owner_or_delegate = company.company_user_id == user_id
        if not is_owner_or_delegate:
            is_owner_or_delegate = CompanyAdminLink.objects.filter(
                company=company, user_id=user_id, status='Accepted'
            ).exists()

        if not is_owner_or_delegate:
            return CustomResponse(general_message="You are not authorized to verify jobs.").get_failure_response(status_code=403)

        job = CompanyJob.objects.filter(id=job_id, company=company, status='Pending Approval').first()
        if not job:
            return CustomResponse(general_message="Job posting not found or not pending approval.").get_failure_response(
                status_code=404)

        serializer = job_serializers.JobVerifySerializer(job, data=request.data, context={'user_id': user_id})
        if serializer.is_valid():
            job = serializer.save()

            try:
                from api.notification.notifications_utils import NotificationUtils
                from django.conf import settings

                status = serializer.validated_data.get('status')
                title = "Job Posting Approved" if status == 'Active' else "Job Posting Rejected"
                description = f"Your job posting '{job.title}' has been {status.lower()}"
                if status == 'Rejected':
                    description += f". Reason: {job.rejection_reason}"

                NotificationUtils.insert_notification(user=job.created_by, title=title, description=description,
                                                      button="View Job",
                                                      url=f"{settings.FR_DOMAIN_NAME}/dashboard/jobs/{job.id}/",
                                                      created_by=company.company_user)
            except Exception:
                pass

            return CustomResponse(
                general_message=f"Job posting has been {job.status.lower()}.",
                response=job_serializers.JobListSerializer(job).data
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

class PublicJobAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Public - Jobs'],
        description="Public endpoint to list all active jobs.",
        responses={200: job_serializers.JobListSerializer(many=True)},
    )
    def get(self, request):
        jobs = CompanyJob.objects.filter(status='Active', is_deleted=False)
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            jobs, request, 
            search_fields=["title", "location", "job_type", "company__name"],
            sort_fields={"title": "title", "created_at": "created_at"}
        )
        
        serializer = job_serializers.JobListSerializer(paginated_queryset.get("queryset"), many=True)
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
        
        job = CompanyJob.objects.filter(id=job_id, status='Active', is_deleted=False).first()
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

        application.delete()
        
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

        if application.status != 'Rejected':
            return CustomResponse(
                general_message="Only rejected applications can be resubmitted."
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


class CompanyAdminLinkAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Admin'],
        description="List all delegates for the authenticated company owner.",
        responses={200: job_serializers.CompanyAdminLinkSerializer(many=True)},
    )
    @role_required([RoleType.COMPANY.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company or company.company_user_id != user_id:
            return CustomResponse(
                general_message="Company profile not found or you are not the owner."
            ).get_failure_response(status_code=403)

        links = CompanyAdminLink.objects.filter(company=company).select_related('user', 'created_by')
        serializer = job_serializers.CompanyAdminLinkSerializer(links, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    @extend_schema(
        tags=['Dashboard - Company Admin'],
        description="Invite a user to be a company delegate.",
        request=inline_serializer(name='CompanyDelegateInviteSerializer', fields={'muid': serializers.CharField()}),
    )
    @role_required([RoleType.COMPANY.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company or company.company_user_id != user_id:
            return CustomResponse(
                general_message="Company profile not found or you are not the owner."
            ).get_failure_response(status_code=403)

        muid = request.data.get('muid')
        if not muid:
            return CustomResponse(general_message="muid is required.").get_failure_response()

        delegate_user = User.objects.filter(muid=muid).first()
        if not delegate_user:
            return CustomResponse(general_message="User not found.").get_failure_response(status_code=404)

        if delegate_user.id == user_id:
            return CustomResponse(general_message="You cannot invite yourself.").get_failure_response()

        link, created = CompanyAdminLink.objects.get_or_create(
            company=company,
            user=delegate_user,
            defaults={
                'status': 'Pending',
                'created_by_id': user_id,
                'updated_by_id': user_id,
            }
        )

        if not created:
            return CustomResponse(
                general_message=f"An invitation for this user is already {link.status.lower()}."
            ).get_failure_response()

        try:
            owner = User.objects.get(id=user_id)
            NotificationUtils.insert_notification(
                user=delegate_user,
                title="Company Delegate Invitation",
                description=f"You have been invited by {owner.full_name} to become a delegate for {company.name}.",
                button="View Invites",
                url=f"{settings.FR_DOMAIN_NAME}/dashboard/company/delegate-invites/",
                created_by=owner,
            )
            SystemActionLog.objects.create(
                action_type=SystemActionLog.ActionType.DELEGATE_INVITED,
                actor_user=owner,
                subject_user=delegate_user,
                entity_name='company_admin_link',
                entity_id=link.id,
                new_data={
                    'company_id': str(company.id),
                    'company_name': company.name,
                    'delegate_muid': delegate_user.muid,
                },
                remarks=f"Company owner {owner.full_name} invited {delegate_user.full_name} as a delegate for {company.name}."
            )
        except Exception:
            pass

        return CustomResponse(
            general_message="Delegate invited successfully. Awaiting their acceptance."
        ).get_success_response()


class CompanyAdminLinkRespondAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Admin'],
        description="Accept or decline a company delegate invitation.",
        request=inline_serializer(name='CompanyDelegateRespondSerializer', fields={'accept': serializers.BooleanField()}),
    )
    def post(self, request, link_id):
        user_id = JWTUtils.fetch_user_id(request)

        link = CompanyAdminLink.objects.filter(id=link_id, user_id=user_id, status='Pending').first()
        if not link:
            return CustomResponse(
                general_message="Invitation not found or already responded to."
            ).get_failure_response(status_code=404)

        accept = request.data.get('accept')
        if accept is None:
            return CustomResponse(general_message="'accept' (true/false) is required.").get_failure_response()

        actor = User.objects.get(id=user_id)
        if accept:
            link.status = 'Accepted'
            link.updated_by_id = user_id
            link.save()
            SystemActionLog.objects.create(
                action_type=SystemActionLog.ActionType.DELEGATE_RESPONDED,
                actor_user=actor,
                subject_user=link.company.company_user,
                entity_name='company_admin_link',
                entity_id=link.id,
                new_data={
                    'company_id': str(link.company.id),
                    'company_name': link.company.name,
                    'response': 'Accepted',
                },
                remarks=f"User {actor.full_name} accepted delegate invitation for {link.company.name}."
            )
            return CustomResponse(general_message="Invitation accepted.").get_success_response()
        else:
            SystemActionLog.objects.create(
                action_type=SystemActionLog.ActionType.DELEGATE_RESPONDED,
                actor_user=actor,
                subject_user=link.company.company_user,
                entity_name='company_admin_link',
                entity_id=link.id,
                new_data={
                    'company_id': str(link.company.id),
                    'company_name': link.company.name,
                    'response': 'Declined',
                },
                remarks=f"User {actor.full_name} declined delegate invitation for {link.company.name}."
            )
            link.delete()
            return CustomResponse(general_message="Invitation declined.").get_success_response()


class CompanyAdminLinkRevokeAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Admin'],
        description="Revoke an accepted company delegate.",
    )
    @role_required([RoleType.COMPANY.value])
    def delete(self, request, link_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company or company.company_user_id != user_id:
            return CustomResponse(
                general_message="Company profile not found or you are not the owner."
            ).get_failure_response(status_code=403)

        link = CompanyAdminLink.objects.filter(id=link_id, company=company, status='Accepted').first()
        if not link:
            return CustomResponse(general_message="Accepted delegate link not found.").get_failure_response(status_code=404)

        owner = User.objects.get(id=user_id)
        delegate_user = link.user
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.DELEGATE_REVOKED,
            actor_user=owner,
            subject_user=delegate_user,
            entity_name='company_admin_link',
            entity_id=link.id,
            old_data={
                'company_id': str(company.id),
                'company_name': company.name,
                'delegate_muid': delegate_user.muid,
            },
            remarks=f"Company owner {owner.full_name} revoked delegate access for {delegate_user.full_name} from {company.name}."
        )
        link.delete()
        return CustomResponse(general_message="Delegate revoked successfully.").get_success_response()


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
