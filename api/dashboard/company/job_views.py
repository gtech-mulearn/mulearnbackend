from utils.utils import DateTimeUtils
from rest_framework.views import APIView
from django.db.models import Q, F
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.job import CompanyJob, UserJobApplication
from db.company import Company
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from . import job_serializers
from .company_views import _get_company_for_user

class CompanyJobAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company Jobs'],
        description=(
            "Post a new job/gig. "
            "Jobs are always created with status='Draft' regardless of any status value sent in the request body. "
            "Use PATCH /jobs/{job_id}/ to change the status to 'Active' (or any other value) after creation."
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

        serializer = job_serializers.JobCreateSerializer(
            data=request.data, context={"user_id": user_id, "company": company}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Job posted successfully.",
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
            return CustomResponse(general_message="Company profile not found or access denied.").get_failure_response(status_code=404)

        jobs = CompanyJob.objects.filter(company=company, is_deleted=False)
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
    authentication_classes = [CustomizePermission]

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
        serializer = job_serializers.JobUpdateSerializer(job, data=request.data, partial=True, context={'user_id': user_id})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Job updated successfully.",
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
        job.updated_by = user_id
        job.save()
        return CustomResponse(general_message="Job deleted successfully.").get_success_response()

class PublicJobAPI(APIView):
    permission_classes = []

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
    authentication_classes = [CustomizePermission]

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
    authentication_classes = [CustomizePermission]

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
    authentication_classes = [CustomizePermission]

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
    authentication_classes = [CustomizePermission]

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
    authentication_classes = [CustomizePermission]

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


class CompanyJobEngagementAnalyticsAPIView(APIView):
    """
    GET /company/jobs/<job_id>/analytics/

    Fetches detailed view, application, and hired statistics for a specific job posting.
    """
    authentication_classes = [CustomizePermission]

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


