from rest_framework.views import APIView
from rest_framework import status
from db.user import User
from db.company import Company, CompanyJob,CompanyJobRule
from utils.permission import JWTUtils, CustomizePermission
from utils.response import CustomResponse
from utils.utils import CommonUtils
from .serializers import CompanyJobCreateSerializer, CompanyJobUpdateSerializer, CompanyJobListSerializer,  JobRuleCreateSerializer,   JobRuleUpdateSerializer 


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
            #     status_code=status.HTTP_404_NOT_FOUND,
                error_code="COMPANY_NOT_FOUND"
            # ).get_failure_response()
            ).get_failure_response(
                    status_code=404,
                    http_status_code=status.HTTP_404_NOT_FOUND
                )
            return False, None, error_response
        
        if company.company_user_id.id != user.id:
            error_response = CustomResponse(
                general_message="You are not authorized to access this company",
                # status_code=status.HTTP_403_FORBIDDEN,
                error_code="UNAUTHORIZED"
            ).get_failure_response(
                    status_code=403,
                    http_status_code=status.HTTP_403_FORBIDDEN
                )
            
            return False, company, error_response
            
        return True, company, None


class ListCompanyJobsAPIView(BaseCompanyJobView):
    """API to list jobs for a specific company."""
    
    def get(self, request):
        try:
            # 1. Get authenticated user
            user = self.get_authenticated_user(request)
            # print(user)
            company = Company.objects.get(company_user_id=user.id)
            if not user:
                return CustomResponse(
                    general_message="User not found",
                    # status_code=status.HTTP_401_UNAUTHORIZED
                ).get_failure_response(
                    status_code=404,
                    http_status_code=status.HTTP_404_NOT_FOUND
                )
            
            # # 2. Check company authorization
            # authorized, company, error_response = self.check_company_authorization(user, company_id=company_id)
            # if not authorized:
            #     return error_response
           ## Check user is linked to a company
            # if not hasattr(user, "company") or not user.company:
            #     return CustomResponse(
            #     general_message="User is not associated with any company",
            #     # status=status.HTTP_403_FORBIDDEN
            # ).get_failure_response(
            #         status_code=403,
            #         http_status_code=status.HTTP_403_FORBIDDEN
            #     )

            # company = user.company
            # 3. Get all active jobs for the company
            # jobs = CompanyJob.objects.filter(
            #     company_id=company,
            #     is_deleted=False
            # ).order_by('-created_at')
            jobs = CompanyJob.objects.filter(
            company_id=company,
            is_deleted=False).prefetch_related("rules")

            paginated_data = CommonUtils.get_paginated_queryset(
            queryset=jobs,
            request=request,
            search_fields=["title", "location", "job_type"],
            sort_fields={
                "title": "title",
                "createdAt": "created_at",
                "salary": "salary_range",
            },
            is_pagination=True)

            jobs_queryset = paginated_data["queryset"]
            pagination_info = paginated_data["pagination"]

            serializer = CompanyJobListSerializer(jobs_queryset, many=True)

            
            # 4. Prepare response with serializer
            jobs_serializer = CompanyJobListSerializer(jobs, many=True)
            
            # response_data = {
            #     "company_id": str(company.id),
            #     "company_name": company.name,
            #     "total_jobs": len(jobs_serializer.data),
            #     "jobs": jobs_serializer.data
            # }
            response_data = {
            "company_id": str(company.id),
            "company_name": company.name,
            "jobs": serializer.data,
            
            "pagination": pagination_info
        }

            
            return CustomResponse(
                response=response_data,
                general_message="Jobs retrieved successfully",
                # status=status.HTTP_200_OK
            ).get_success_response()
            
        except Exception as e:
            print(f"Error listing company jobs: {str(e)}")
            # return CustomResponse(
            #     general_message="Something went wrong",
            #     # status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              
            # ).get_failure_response(
            #         status_code=500,
            #         http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            #     )
            return CustomResponse(
                general_message="Something went wrong in listing company jobs",
                message={"error_code": "SERVER_ERROR"}
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    


class CreateCompanyJobAPIView(BaseCompanyJobView):
    
    def post(self, request):
        try:
            # 1. Get authenticated user
            user = self.get_authenticated_user(request)
            if not user:
                # return CustomResponse(
                #     general_message="User not found",
                #     status_code=status.HTTP_401_UNAUTHORIZED
                # ).get_failure_response()
                return CustomResponse(
                    general_message="User not found"
                ).get_failure_response(
                    status_code=401,
                    http_status_code=status.HTTP_401_UNAUTHORIZED
                )
         
            
            try:
                company = Company.objects.get(
                    company_user_id=user, 
                    deleted_at__isnull=True,
                    status='active'
                )
              
            except Company.DoesNotExist:
                print(f"No company found for user: {user.id}")
                # return CustomResponse(
                #     general_message="No active company found for user",
                #     status_code=status.HTTP_404_NOT_FOUND,
                #     error_code="NO_COMPANY_FOUND"
                # ).get_failure_response()

                return CustomResponse(
                    general_message="No active company found for user",
                    message={"error_code": "NO_COMPANY_FOUND"}
                ).get_failure_response(
                    status_code=404,
                    http_status_code=status.HTTP_404_NOT_FOUND
                )

            # 2. Validate request data
            print(f"Request data: {request.data}")
            serializer = CompanyJobCreateSerializer(data=request.data)
            if not serializer.is_valid():
                # return CustomResponse(
                #     message=serializer.errors,
                #     status_code=status.HTTP_400_BAD_REQUEST,
                #     error_code="INVALID_INPUT"
                # ).get_failure_response()
                return CustomResponse(
                    message=serializer.errors,
                    general_message="Invalid input data"
                ).get_failure_response(
                    status_code=400,
                    http_status_code=status.HTTP_400_BAD_REQUEST
                )
           
            
            
            # company_id = serializer.validated_data['company_id']
            
            # # 3. Check company authorization
            # authorized, company, error_response = self.check_company_authorization(user, company_id=company_id)
            # if not authorized:
            #     return error_response
            # if company.status != 'active':
            #     return CustomResponse(
            #         general_message="Company is not active",
            #         status_code=status.HTTP_400_BAD_REQUEST,
            #         error_code="COMPANY_INACTIVE"
            #     ).get_failure_response()
            
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
            print(f"Job data before creation: {job_data}")
            job = CompanyJob.objects.create(**job_data)
            print(f"Job created successfully: {job.id}")  # D
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
                # status_code=status.HTTP_201_CREATED
            ).get_success_response()
            
        except Exception as e:
            # Log the actual error for debugging
            # print(f"Error creating company job: {str(e)}")
  
            
            # return CustomResponse(
            #     general_message="Something went wrong",
            #     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            #     error_code="SERVER_ERROR"
            # ).get_failure_response()
            return CustomResponse(
                general_message="Something went wrong",
                message={"error_code": "SERVER_ERROR"}
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateCompanyJobAPIView(BaseCompanyJobView):
    
    def patch(self, request, job_id):
        try:
            # 1. Get authenticated user
            user = self.get_authenticated_user(request)
            if not user:
                return CustomResponse(
                    general_message="User not found"
                ).get_failure_response(
                    status_code=401,
                    http_status_code=status.HTTP_401_UNAUTHORIZED
                )

            # 2. Get the job to update
            try:
                job = CompanyJob.objects.get(id=job_id, is_deleted=False)
            except CompanyJob.DoesNotExist:
                # return CustomResponse(
                #     general_message="Job does not exist",
                #     status=status.HTTP_404_NOT_FOUND,
                #     error_code="JOB_NOT_FOUND"
                # ).get_failure_response()
                
                return CustomResponse(
                    general_message="Job does not exist",
                    message={"error_code": "NO_JOB_FOUND"}
                ).get_failure_response(
                    status_code=404,
                    http_status_code=status.HTTP_404_NOT_FOUND
                )
            
            # 3. Check company authorization
            authorized, company, error_response = self.check_company_authorization(user, job=job)
            if not authorized:
                return error_response
            
            # 4. Validate request data (partial update)
            serializer = CompanyJobUpdateSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                # return CustomResponse(
                #     message=serializer.errors,
                #     status=status.HTTP_400_BAD_REQUEST,
                #     error_code="INVALID_INPUT"
                # ).get_failure_response()
                return CustomResponse(
                    message=serializer.errors,
                    general_message="Invalid input data"
                ).get_failure_response(
                    status_code=400,
                    http_status_code=status.HTTP_400_BAD_REQUEST
                )
           
            
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
                # "updated_at": job.updated_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            
            # return CustomResponse(
            #     response=response_data,
            #     general_message="Job updated successfully",
            #     status=status.HTTP_200_OK
            # ).get_success_response()
            return CustomResponse(
                response=response_data,
                general_message="Job updated successfully",
                # status_code=status.HTTP_201_CREATED
            ).get_success_response()
            
        except Exception as e:
            # Log the actual error for debugging
            print(f"Error updating company job: {str(e)}")
            # return CustomResponse(
            #     general_message="Something went wrong",
            #     status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            #     error_code="SERVER_ERROR"
            # ).get_failure_response()
            return CustomResponse(
                general_message="Something went wrong in updating the job",
                message={"error_code": "SERVER_ERROR"}
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, job_id):
        try:
            # 1. Get authenticated user
            user = self.get_authenticated_user(request)
            if not user:
                return CustomResponse(
                    general_message="User not found",
                    status=status.HTTP_401_UNAUTHORIZED
                ).get_failure_response()

            # 2. Get the job to delete
            try:
                job = CompanyJob.objects.get(id=job_id, is_deleted=False)
            except CompanyJob.DoesNotExist:
                return CustomResponse(
                    general_message="Job does not exist",
                    status=status.HTTP_404_NOT_FOUND,
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
                status=status.HTTP_200_OK
            ).get_success_response()
            
        except Exception as e:
            # Log the actual error for debugging
            print(f"Error deleting company job: {str(e)}")
            return CustomResponse(
                general_message="Something went wrong",
                # status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="SERVER_ERROR"
            ).get_failure_response()


class CreateJobRuleAPIView(BaseCompanyJobView):
    """API to create eligibility rules for a job."""
    
    def post(self, request, job_id):
        try:
            # 1. Get authenticated user
            user = self.get_authenticated_user(request)
            if not user:
                return CustomResponse(
                    general_message="User not found"
                ).get_failure_response(
                    status_code=401,
                    http_status_code=status.HTTP_401_UNAUTHORIZED
                )

            # 2. Get the job
            try:
                job = CompanyJob.objects.get(id=job_id)
            except CompanyJob.DoesNotExist:
                return CustomResponse(
                    general_message="Job does not exist",
                    message={"error_code": "JOB_NOT_FOUND"}
                ).get_failure_response(
                    status_code=404,
                    http_status_code=status.HTTP_404_NOT_FOUND
                )

            # 3. Check company authorization
            authorized, company, error_response = self.check_company_authorization(user, job=job)
            if not authorized:
                return error_response

            # 4. Validate request data
            serializer = JobRuleCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return CustomResponse(
                    general_message="Invalid input data",
                    message={"validation_errors": serializer.errors}
                ).get_failure_response(
                    status_code=400,
                    http_status_code=status.HTTP_400_BAD_REQUEST
                )

            rule_type = serializer.validated_data['rule_type']
            rule_type_id = serializer.validated_data['rule_type_id']

            # 5. Check for duplicate rule
            existing_rule = CompanyJobRule.objects.filter(
                job_id=job,
                rule_type=rule_type,
                rule_type_id=rule_type_id,
            
            ).first()
            
            if existing_rule:
                return CustomResponse(
                    general_message="This rule already exists for the job",
                    message={"error_code": "DUPLICATE_RULE"}
                ).get_failure_response(
                    status_code=400,
                    http_status_code=status.HTTP_400_BAD_REQUEST
                )

            # 6. Create the job rule
            job_rule = CompanyJobRule.objects.create(
                job_id=job_id,
                rule_type=rule_type,
                rule_type_id=rule_type_id
            )

            # 7. Prepare response
            response_data = {
                "job_rule": {
                    "id": str(job_rule.id),
                    "job_id": str(job.id),
                    "rule_type": job_rule.rule_type,
                    "rule_type_id": job_rule.rule_type_id,
                    "created_at": job_rule.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')
                }
            }

            return CustomResponse(
                general_message="Job rule added successfully",
                response=response_data
            ).get_success_response()

        except Exception as e:
            print(f"Error creating job rule: {str(e)}")
            return CustomResponse(
                general_message="Something went wrong",
                message={"error_code": "SERVER_ERROR"}
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class UpdateJobRuleAPIView(BaseCompanyJobView):
    """API to update a specific job rule."""
    
    def patch(self, request, job_id, rule_id):
        try:
            # 1. Get authenticated user
            user = self.get_authenticated_user(request)
            if not user:
                return CustomResponse(
                    general_message="User not found"
                ).get_failure_response(
                    status_code=401,
                    http_status_code=status.HTTP_401_UNAUTHORIZED
                )

            # 2. Get the job
            try:
                job = CompanyJob.objects.get(id=job_id)
            except CompanyJob.DoesNotExist:
                return CustomResponse(
                    general_message="Job does not exist",
                    message={"error_code": "JOB_NOT_FOUND"}
                ).get_failure_response(
                    status_code=404,
                    http_status_code=status.HTTP_404_NOT_FOUND
                )

            # 3. Check company authorization
            authorized, company, error_response = self.check_company_authorization(user, job=job)
            if not authorized:
                return error_response

            # 4. Get the job rule
            try:
                job_rule = CompanyJobRule.objects.get(
                    id=rule_id,
                    job_id=job,
               
                )
            except CompanyJobRule.DoesNotExist:
                return CustomResponse(
                    general_message="Job rule does not exist",
                    message={"error_code": "RULE_NOT_FOUND"}
                ).get_failure_response(
                    status_code=404,
                    http_status_code=status.HTTP_404_NOT_FOUND
                )

            # 5. Validate request data
            serializer = JobRuleUpdateSerializer(job_rule, data=request.data, partial=True)
            if not serializer.is_valid():
                return CustomResponse(
                    general_message="Invalid input data",
                    message={"validation_errors": serializer.errors, "error_code": "INVALID_INPUT"}
                ).get_failure_response(
                    status_code=400,
                    http_status_code=status.HTTP_400_BAD_REQUEST
                )

            new_rule_type_id = serializer.validated_data.get('rule_type_id')
            # new_rule_name = serializer.validated_data.get('rule_name')

            # 6. Check for duplicate rule (if rule_type_id is being changed)
            if new_rule_type_id and new_rule_type_id != job_rule.rule_type_id:
                existing_rule = CompanyJobRule.objects.filter(
                    job_id=job,
                    rule_type=job_rule.rule_type,
                    rule_type_id=new_rule_type_id,
                    
                ).exclude(id=job_rule.id).first()
                
                if existing_rule:
                    return CustomResponse(
                        general_message="A rule with this value already exists for the job",
                        message={"error_code": "DUPLICATE_RULE"}
                    ).get_failure_response(
                        status_code=400,
                        http_status_code=status.HTTP_400_BAD_REQUEST
                    )

            # 7. Update the job rule
            old_value =job_rule.rule_type_id
            
            if new_rule_type_id:
                job_rule.rule_type_id = new_rule_type_id
       
                
            job_rule.save()

            # 8. Prepare response
            response_data = {
                "rule_id": str(job_rule.id),
                "updated_value": job_rule.rule_type_id,
                # "updated_at": job_rule.updated_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            }

            return CustomResponse(
                general_message="Job rule updated successfully",
                response=response_data
            ).get_success_response()

        except Exception as e:
            import traceback
            print(f"Error updating job rule: {str(e)}")
            print(f"Full traceback: {traceback.format_exc()}")
            return CustomResponse(
                general_message="Something went wrong",
                message={"error_code": "SERVER_ERROR", "details": str(e)}
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )