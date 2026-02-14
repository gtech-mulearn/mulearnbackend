from rest_framework.views import APIView
from rest_framework import status
from db.user import User
from db.company import Company, CompanyJob
from utils.permission import JWTUtils, CustomizePermission
from utils.response import CustomResponse
from utils.types import OrganizationType
from utils.utils import CommonUtils
from .serializers import CompanyJobCreateSerializer, CompanyJobUpdateSerializer, CompanyJobListSerializer


class BaseCompanyJobView(APIView):
    """Base view for common functionality across company job views."""
    permission_classes = [CustomizePermission]
    
    def get_authenticated_user(self, request):
        """Get the authenticated user from JWT token."""
        user_id = JWTUtils.fetch_user_id(request)
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    def check_company_authorization(self, user, company_id=None, job=None):
        """Check if user is authorized to access the company.
        
        Args:
            user: The authenticated user
            company_id: Company ID (used when creating jobs)
            job: CompanyJob object (used when updating/deleting jobs)
            
        Returns:
            tuple: (authorized: bool, company: Company, error_response: dict)
        """
        try:
            if job:
                company = job.company_id
            else:
                company = Company.objects.get(id=company_id, deleted_at__isnull=True)
        except Company.DoesNotExist:
            error_response = CustomResponse(
                general_message="Company does not exist",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="COMPANY_NOT_FOUND"
            ).get_failure_response()
            return False, None, error_response
        
        if company.company_user_id.id != user.id:
            error_response = CustomResponse(
                general_message="You are not authorized to access this company",
                status_code=status.HTTP_403_FORBIDDEN,
                error_code="UNAUTHORIZED"
            ).get_failure_response()
            return False, company, error_response
            
        return True, company, None


class ListCompanyJobsAPIView(BaseCompanyJobView):
    """API to list jobs for a specific company."""
    
    def get(self, request, company_id):
        try:
            # 1. Get authenticated user
            user = self.get_authenticated_user(request)
            if not user:
                return CustomResponse(
                    general_message="User not found",
                    status_code=status.HTTP_401_UNAUTHORIZED
                ).get_failure_response()
            
            # 2. Check company authorization
            authorized, company, error_response = self.check_company_authorization(user, company_id=company_id)
            if not authorized:
                return error_response
            
            # 3. Get all active jobs for the company
            jobs = CompanyJob.objects.filter(
                company_id=company,
                is_deleted=False
            ).order_by('-created_at')
            
            # 4. Prepare response with serializer
            jobs_serializer = CompanyJobListSerializer(jobs, many=True)
            
            response_data = {
                "company_id": str(company.id),
                "company_name": company.title,
                "total_jobs": len(jobs_serializer.data),
                "jobs": jobs_serializer.data
            }
            
            return CustomResponse(
                response=response_data,
                general_message="Jobs retrieved successfully",
                status_code=status.HTTP_200_OK
            ).get_success_response()
            
        except Exception as e:
            print(f"Error listing company jobs: {str(e)}")
            return CustomResponse(
                general_message="Something went wrong",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="SERVER_ERROR"
            ).get_failure_response()


class CreateCompanyJobAPIView(BaseCompanyJobView):
    
    def post(self, request):
        try:
            # 1. Get authenticated user
            user = self.get_authenticated_user(request)
            if not user:
                return CustomResponse(
                    general_message="User not found",
                    status_code=status.HTTP_401_UNAUTHORIZED
                ).get_failure_response()

            # 2. Validate request data
            serializer = CompanyJobCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return CustomResponse(
                    message=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="INVALID_INPUT"
                ).get_failure_response()
            
            company_id = serializer.validated_data['company_id']
            
            # 3. Check company authorization
            authorized, company, error_response = self.check_company_authorization(user, company_id=company_id)
            if not authorized:
                return error_response
            if company.status != 'active':
                return CustomResponse(
                    general_message="Company is not active",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="COMPANY_INACTIVE"
                ).get_failure_response()
            
            # 6. Create the job
            job_data = {
                'company_id': company,
                'title': serializer.validated_data['title'],
                'experience': serializer.validated_data.get('experience'),
                'job_description': serializer.validated_data.get('job_description'),
                'location': serializer.validated_data.get('location'),
                'salary_range': serializer.validated_data.get('salary_range'),
                'job_type': serializer.validated_data['job_type'],
                'min_karma': serializer.validated_data.get('min_karma', 0),
                'min_level': serializer.validated_data.get('min_level', 0),
                'status': 'Active'
            }
            
            job = CompanyJob.objects.create(**job_data)
            
            # 6. Prepare response
            response_data = {
                "job": {
                    "id": str(job.id),
                    "company_id": str(job.company_id.id),
                    "title": job.title,
                    "job_type": job.job_type,
                    "created_at": job.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')
                }
            }
            
            return CustomResponse(
                response=response_data,
                general_message="Job created successfully",
                status_code=status.HTTP_201_CREATED
            ).get_success_response()
            
        except Exception as e:
            # Log the actual error for debugging
            print(f"Error creating company job: {str(e)}")
            return CustomResponse(
                general_message="Something went wrong",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="SERVER_ERROR"
            ).get_failure_response()


class UpdateCompanyJobAPIView(BaseCompanyJobView):
    
    def patch(self, request, job_id):
        try:
            # 1. Get authenticated user
            user = self.get_authenticated_user(request)
            if not user:
                return CustomResponse(
                    general_message="User not found",
                    status_code=status.HTTP_401_UNAUTHORIZED
                ).get_failure_response()

            # 2. Get the job to update
            try:
                job = CompanyJob.objects.get(id=job_id, is_deleted=False)
            except CompanyJob.DoesNotExist:
                return CustomResponse(
                    general_message="Job does not exist",
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code="JOB_NOT_FOUND"
                ).get_failure_response()
            
            # 3. Check company authorization
            authorized, company, error_response = self.check_company_authorization(user, job=job)
            if not authorized:
                return error_response
            
            # 4. Validate request data (partial update)
            serializer = CompanyJobUpdateSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                return CustomResponse(
                    message=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="INVALID_INPUT"
                ).get_failure_response()
            
            # 5. Track which fields are being updated
            validated_data = serializer.validated_data
            updated_fields = list(validated_data.keys())
            
            # 6. Update the job with validated data
            for field, value in validated_data.items():
                setattr(job, field, value)
            
            job.save()
            
            # 7. Prepare response
            response_data = {
                "job_id": str(job.id),
                "updated_fields": updated_fields,
                "updated_at": job.updated_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            
            return CustomResponse(
                response=response_data,
                general_message="Job updated successfully",
                status_code=status.HTTP_200_OK
            ).get_success_response()
            
        except Exception as e:
            # Log the actual error for debugging
            print(f"Error updating company job: {str(e)}")
            return CustomResponse(
                general_message="Something went wrong",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="SERVER_ERROR"
            ).get_failure_response()
    
    def delete(self, request, job_id):
        try:
            # 1. Get authenticated user
            user = self.get_authenticated_user(request)
            if not user:
                return CustomResponse(
                    general_message="User not found",
                    status_code=status.HTTP_401_UNAUTHORIZED
                ).get_failure_response()

            # 2. Get the job to delete
            try:
                job = CompanyJob.objects.get(id=job_id, is_deleted=False)
            except CompanyJob.DoesNotExist:
                return CustomResponse(
                    general_message="Job does not exist",
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code="JOB_NOT_FOUND"
                ).get_failure_response()
            
            # 3. Check company authorization
            authorized, company, error_response = self.check_company_authorization(user, job=job)
            if not authorized:
                return error_response
            
            # 4. Soft delete the job (set is_deleted to True)
            job.is_deleted = True
            job.save()
            
            # 5. Prepare response
            response_data = {
                "job_id": str(job.id),
                "deleted_at": job.updated_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            
            return CustomResponse(
                response=response_data,
                general_message="Job deleted successfully",
                status_code=status.HTTP_200_OK
            ).get_success_response()
            
        except Exception as e:
            # Log the actual error for debugging
            print(f"Error deleting company job: {str(e)}")
            return CustomResponse(
                general_message="Something went wrong",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="SERVER_ERROR"
            ).get_failure_response()
