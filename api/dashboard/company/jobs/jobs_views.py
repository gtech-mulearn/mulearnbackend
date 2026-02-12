from rest_framework.views import APIView
from rest_framework import status
from db.user import User
from db.company import Company, CompanyJob
from utils.permission import JWTUtils
from utils.response import CustomResponse
from utils.types import OrganizationType
from utils.utils import CommonUtils
from .serializers import CompanyJobCreateSerializer


class CreateCompanyJobAPIView(APIView):
    
    def post(self, request):
        try:
            # 1. JWT Authentication
            user_id = JWTUtils.fetch_user_id(request)
            if not user_id:
                return CustomResponse(
                    general_message="Authentication required",
                    status_code=status.HTTP_401_UNAUTHORIZED
                ).get_failure_response()
            
            # 2. Get authenticated user
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return CustomResponse(
                    general_message="User not found",
                    status_code=status.HTTP_401_UNAUTHORIZED
                ).get_failure_response()
            
            # 3. Validate request data
            serializer = CompanyJobCreateSerializer(data=request.data)
            if not serializer.is_valid():
                error_message = CommonUtils.get_first_error_message_from_serializer_errors(
                    serializer.errors, "job_type must be one of the allowed values"
                )
                return CustomResponse(
                    general_message=error_message,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="INVALID_INPUT"
                ).get_failure_response()
            
            company_id = serializer.validated_data['company_id']
            
            # 4. Check if company exists
            try:
                company = Company.objects.get(id=company_id, is_deleted=False)
            except Company.DoesNotExist:
                return CustomResponse(
                    general_message="Company does not exist",
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code="COMPANY_NOT_FOUND"
                ).get_failure_response()
            
            # 5. AUTHORIZATION CHECK: Is user the company admin?
            if company.company_user_id.id != user.id:
                return CustomResponse(
                    general_message="You are not authorized to create jobs for this company",
                    status_code=status.HTTP_403_FORBIDDEN,
                    error_code="UNAUTHORIZED"
                ).get_failure_response()
            
            # 6. Check if company is active
            if company.status != 'active':
                return CustomResponse(
                    general_message="Company is not active",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="COMPANY_INACTIVE"
                ).get_failure_response()
            
            # 7. Create the job
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
            
            # 8. Prepare response
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
            CommonUtils.log_error(f"Error creating company job: {str(e)}")
            return CustomResponse(
                general_message="Something went wrong",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="SERVER_ERROR"
            ).get_failure_response()    