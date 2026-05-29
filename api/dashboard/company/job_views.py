from utils.utils import DateTimeUtils
from rest_framework.views import APIView
from django.db.models import Q
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.job import CompanyJob, UserJobApplication
from db.company import Company
from . import job_serializers

class CompanyJobAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required([RoleType.COMPANY.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = job_serializers.JobCreateSerializer(
            data=request.data, context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Job posted successfully.",
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.COMPANY.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id).first()
        
        if not company:
            return CustomResponse(general_message="Company profile not found.").get_failure_response(status_code=404)

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
    permission_classes = [CustomizePermission]

    @role_required([RoleType.COMPANY.value])
    def get(self, request, job_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id).first()
        
        job = CompanyJob.objects.filter(id=job_id, company=company, is_deleted=False).first()
        if not job:
            return CustomResponse(general_message="Job not found.").get_failure_response(status_code=404)
            
        serializer = job_serializers.JobListSerializer(job)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.COMPANY.value])
    def patch(self, request, job_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id).first()
        
        job = CompanyJob.objects.filter(id=job_id, company=company, is_deleted=False).first()
        if not job:
            return CustomResponse(general_message="Job not found.").get_failure_response(status_code=404)
            
        serializer = job_serializers.JobUpdateSerializer(job, data=request.data, partial=True, context={'user_id': user_id})
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Job updated successfully.",
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.COMPANY.value])
    def delete(self, request, job_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id).first()
        
        job = CompanyJob.objects.filter(id=job_id, company=company, is_deleted=False).first()
        if not job:
            return CustomResponse(general_message="Job not found.").get_failure_response(status_code=404)
            
        job.is_deleted = True
        job.updated_at = DateTimeUtils.get_current_utc_time()
        job.updated_by = user_id
        job.save()
        
        return CustomResponse(general_message="Job deleted successfully.").get_success_response()

class PublicJobAPI(APIView):
    permission_classes = [CustomizePermission]

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

    @role_required([RoleType.COMPANY.value])
    def get(self, request, job_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id).first()

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

    @role_required([RoleType.COMPANY.value])
    def patch(self, request, app_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id).first()

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
