from pytz import timezone
from rest_framework.views import APIView
from rest_framework import status
from db.user import User
from db.company import Company, CompanyJob,CompanyJobRule
from utils.permission import JWTUtils, CustomizePermission
from utils.response import CustomResponse
from utils.utils import CommonUtils
from .serializers import CompanyJobCreateSerializer, CompanyJobUpdateSerializer, CompanyJobListSerializer,  JobRuleCreateSerializer,   JobRuleUpdateSerializer 
from db.skill import Skill 
from db.task import InterestGroup  
from db.achievement import Achievement
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s

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
                company = Company.objects.get(id=company_id, status='active')
        except Company.DoesNotExist:
            error_response = CustomResponse(
                general_message="Company does not exist",
                message={"error_code": "COMPANY_NOT_FOUND"},
            ).get_failure_response(
                status_code=404,
                http_status_code=status.HTTP_404_NOT_FOUND
            )
            return False, None, error_response
        
        if company.company_user_id.id != user.id:
            error_response = CustomResponse(
                general_message="You are not authorized to access this company",
                message={"error_code": "UNAUTHORIZED"},
            ).get_failure_response(
                status_code=403,
                http_status_code=status.HTTP_403_FORBIDDEN
            )
            
            return False, company, error_response
            
        return True, company, None

    @staticmethod
    def get_optimized_jobs_with_rules(company, filters=None):
        """Fetch jobs with optimized rule loading to prevent N+1 queries."""
        # Base queryset
        jobs_qs = CompanyJob.objects.filter(company_id=company, is_deleted=False)
        
        if filters:
            jobs_qs = jobs_qs.filter(**filters)
        
        # Get all jobs with rules in 2 queries
        jobs = list(jobs_qs.prefetch_related('rules').all())
        
        # Collect all rule type IDs by type
        skill_ids = set()
        interest_ids = set()
        achievement_ids = set()
    
        
        for job in jobs:
            for rule in job.rules.all():
                if rule.rule_type == 'skill':
                    skill_ids.add(rule.rule_type_id)
                elif rule.rule_type == 'interest_group':
                    interest_ids.add(rule.rule_type_id)
                elif rule.rule_type == 'achievement':
                    achievement_ids.add(rule.rule_type_id)
        
        # Bulk fetch all related objects (3 queries max)
        skills_map = {str(s.id): s.name for s in Skill.objects.filter(id__in=skill_ids)} if skill_ids else {}
        interests_map = {str(i.id): i.name for i in InterestGroup.objects.filter(id__in=interest_ids)} if interest_ids else {}
        achievements_map = {str(a.id): a.name for a in Achievement.objects.filter(id__in=achievement_ids)} if achievement_ids else {}
        
        # Cache the names directly on rules
        for job in jobs:
            for rule in job.rules.all():
                if rule.rule_type == 'skill':
                    rule.cached_name = skills_map.get(str(rule.rule_type_id), 'Unknown Skill')
                elif rule.rule_type == 'interest_group':
                    rule.cached_name = interests_map.get(str(rule.rule_type_id), 'Unknown Interest')
                elif rule.rule_type == 'achievement':
                    rule.cached_name = achievements_map.get(str(rule.rule_type_id), 'Unknown Achievement')
                else:
                    rule.cached_name = 'Unknown Rule Type'
        
        return jobs


class ListCompanyJobsAPIView(BaseCompanyJobView):
    """API to list jobs for a specific company."""
    
    @extend_schema(
        tags=['Dashboard - Company - Jobs'],
        description="Retrieve List Company Jobs.",
        responses={200: CompanyJobListSerializer},
    )
    def get(self, request):
        try:
            # 1. Get authenticated user FIRST
            user = self.get_authenticated_user(request)
            if not user:
                return CustomResponse(
                    general_message="User not found"
                ).get_failure_response(
                    status_code=401,  # Should be 401, not 404
                    http_status_code=status.HTTP_401_UNAUTHORIZED
                )

            # 2. Get company AFTER user validation
            try:
                company = Company.objects.get(
                    company_user_id=user,  # Use user object, not user.id
                    status='active'  # Remove deleted_at filter based on our previous discussion
                )
            except Company.DoesNotExist:
                return CustomResponse(
                    general_message="No active company found for user",
                    message={"error_code": "NO_COMPANY_FOUND"}
                ).get_failure_response(
                    status_code=404,
                    http_status_code=status.HTTP_404_NOT_FOUND
                )

            # 3. Get base queryset for pagination FIRST
            jobs_qs = CompanyJob.objects.filter(
                company_id=company,
                is_deleted=False
            ).prefetch_related('rules').order_by('-created_at')

            # 4. Apply pagination before optimization
            paginated_data = CommonUtils.get_paginated_queryset(
                queryset=jobs_qs,
                request=request,
                search_fields=["title", "location", "job_type"],
                sort_fields={
                    "title": "title",
                    "createdAt": "created_at", 
                    "salary": "salary_range",
                },
                is_pagination=True
            )
            
      
            pagination_info = paginated_data["pagination"]
            
            # 5. Evaluate paginated queryset once with prefetch (no double-fetch)
            paginated_jobs = list(
                paginated_data["queryset"]
            )

            if paginated_jobs:
                # Collect rule type IDs
                skill_ids, interest_ids, achievement_ids = set(), set(), set()
                for job in paginated_jobs:
                    for rule in job.rules.all():
                        if rule.rule_type == 'skill':
                            skill_ids.add(rule.rule_type_id)
                        elif rule.rule_type == 'interest_group':
                            interest_ids.add(rule.rule_type_id)
                        elif rule.rule_type == 'achievement':
                            achievement_ids.add(rule.rule_type_id)

                # Bulk fetch name maps (3 queries max)
                skills_map = {str(s.id): s.name for s in Skill.objects.filter(id__in=skill_ids)} if skill_ids else {}
                interests_map = {str(i.id): i.name for i in InterestGroup.objects.filter(id__in=interest_ids)} if interest_ids else {}
                achievements_map = {str(a.id): a.name for a in Achievement.objects.filter(id__in=achievement_ids)} if achievement_ids else {}

                # Cache names on rules
                for job in paginated_jobs:
                    for rule in job.rules.all():
                        if rule.rule_type == 'skill':
                            rule.cached_name = skills_map.get(str(rule.rule_type_id), 'Unknown Skill')
                        elif rule.rule_type == 'interest_group':
                            rule.cached_name = interests_map.get(str(rule.rule_type_id), 'Unknown Interest')
                        elif rule.rule_type == 'achievement':
                            rule.cached_name = achievements_map.get(str(rule.rule_type_id), 'Unknown Achievement')
                        else:
                            rule.cached_name = 'Unknown Rule Type'

            # 6. Serialize (order preserved naturally from paginated queryset)
            serializer = CompanyJobListSerializer(paginated_jobs, many=True)
            # ...existing code...
            
            response_data = {
                "company_id": str(company.id),
                "company_name": company.name,
                "jobs": serializer.data,
                "pagination": pagination_info
            }

            return CustomResponse(
                response=response_data,
                general_message="Jobs retrieved successfully"
            ).get_success_response()
            
        except Exception as e:
            print(f"Error listing company jobs: {str(e)}")
            return CustomResponse(
                general_message="Something went wrong in listing company jobs",
                message={"error_code": "SERVER_ERROR"}
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    


class CreateCompanyJobAPIView(BaseCompanyJobView):
    
    @extend_schema(
        tags=['Dashboard - Company - Jobs'],
        description="Create Create Company Job.",
        request=CompanyJobCreateSerializer,
        responses={200: CompanyJobCreateSerializer},
    )
    def post(self, request):
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
            
            
            try:
                company = Company.objects.get(
                    company_user_id=user,
                    status='active'
                )
             
              
            except Company.DoesNotExist:
                print(f"No company found for user: {user}")
           
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
           
                return CustomResponse(
                    message=serializer.errors,
                    general_message="Invalid input data"
                ).get_failure_response(
                    status_code=400,
                    http_status_code=status.HTTP_400_BAD_REQUEST
                )
           
            
            # 6. Create the job
            job_data = {
                'company_id':    company,
                'title':         serializer.validated_data['title'],
                'experience':    serializer.validated_data.get('experience'),
                'job_description': serializer.validated_data.get('job_description'),
                'location':      serializer.validated_data.get('location'),
                'salary_range':  serializer.validated_data.get('salary_range'),
                'job_type':      serializer.validated_data['job_type'],
                'min_karma':     serializer.validated_data.get('min_karma', 0),
                'min_level':     serializer.validated_data.get('min_level', 0),
                'status':        'Active',
                # Enhancement fields
                'karma_reward':         serializer.validated_data.get('karma_reward'),
                'duration_value':       serializer.validated_data.get('duration_value'),
                'duration_unit':        serializer.validated_data.get('duration_unit'),
                'hourly_rate':          serializer.validated_data.get('hourly_rate'),
                'deliverables':         serializer.validated_data.get('deliverables'),
                'stipend':              serializer.validated_data.get('stipend'),
                'certificate_provided': serializer.validated_data.get('certificate_provided'),
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
            print(e)
            return CustomResponse(
                general_message="Something went wrong",
                message={"error_code": "SERVER_ERROR"}
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GetCompanyJobDetailsAPIView(BaseCompanyJobView):
    """API view for retrieving specific job posting details with optimized rules."""
    
    @extend_schema(
        tags=['Dashboard - Company - Jobs'],
        description="Retrieve Get Company Job Details.",
        responses={200: CompanyJobListSerializer},
    )
    def get(self, request, job_id):
        try:
            # 1. Get authenticated user FIRST (same pattern as ListCompanyJobsAPIView)
            user = self.get_authenticated_user(request)
            if not user:
                return CustomResponse(
                    general_message="User not found"
                ).get_failure_response(
                    status_code=401,
                    http_status_code=status.HTTP_401_UNAUTHORIZED
                )

            # 2. Check if job exists and get company (same pattern)
            try:
                job_check = CompanyJob.objects.get(id=job_id, is_deleted=False)
                company = job_check.company_id
            except CompanyJob.DoesNotExist:
                return CustomResponse(
                    general_message="Job does not exist",
                    message={"error_code": "JOB_NOT_FOUND"}
                ).get_failure_response(
                    status_code=404,
                    http_status_code=status.HTTP_404_NOT_FOUND
                )

            # 3. Use SAME N+1 optimization pattern (for single job)
            optimized_jobs = self.get_optimized_jobs_with_rules(
                company, 
                filters={'id': job_id}  # Only get this specific job
            )
            
            if not optimized_jobs:
                return CustomResponse(
                    general_message="Job not found",
                    message={"error_code": "JOB_NOT_FOUND"}
                ).get_failure_response(
                    status_code=404,
                    http_status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Get the optimized job (only one)
            optimized_job = optimized_jobs[0]

            # 4. Use SAME serializer pattern (includes rules with cached names!)
            serializer = CompanyJobListSerializer(optimized_job)
            
            response_data = {
                "job": serializer.data  # Includes rules with cached names!
            }

            return CustomResponse(
                response=response_data,
                general_message="Job details fetched successfully"
            ).get_success_response()

        except Exception as e:
            print(f"Error fetching job details: {str(e)}")
            return CustomResponse(
                general_message="Something went wrong",
                message={"error_code": "SERVER_ERROR"}
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateCompanyJobAPIView(BaseCompanyJobView):
    
    @extend_schema(
        tags=['Dashboard - Company - Jobs'],
        description="Partially update Update Company Job.",
        request=CompanyJobUpdateSerializer,
        responses={200: CompanyJobUpdateSerializer},
    )
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
        
            }
           
            return CustomResponse(
                response=response_data,
                general_message="Job updated successfully",
                # status_code=status.HTTP_201_CREATED
            ).get_success_response()
            
        except Exception as e:
            # Log the actual error for debugging
            print(f"Error updating company job: {str(e)}")
  
            return CustomResponse(
                general_message="Something went wrong in updating the job",
                message={"error_code": "SERVER_ERROR"}
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(tags=['Dashboard - Company - Jobs'], description="Delete Update Company Job.",
        responses={200: CompanyJobUpdateSerializer},
    )
    def delete(self, request, job_id):
        try:
            # 1. Get authenticated user
            user = self.get_authenticated_user(request)
            if not user:
                return CustomResponse(
                    general_message="User not found",
                    # status=status.HTTP_401_UNAUTHORIZED
                ).get_failure_response(
                status_code=401,
                http_status_code=status.HTTP_401_UNAUTHORIZED
            )

            # 2. Get the job to delete
            try:
                job = CompanyJob.objects.get(id=job_id, is_deleted=False)
            except CompanyJob.DoesNotExist:
                return CustomResponse(
                    general_message="Job does not exist",
                    # status=status.HTTP_404_NOT_FOUND,
                    # error_code="JOB_NOT_FOUND"
                ).get_failure_response(
                status_code=404,
                http_status_code=status.HTTP_404_NOT_FOUND
            )
            
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
          
            ).get_success_response()
            
        except Exception as e:
            # Log the actual error for debugging
            print(f"Error deleting company job: {str(e)}")
            return CustomResponse(
                general_message="Something went wrong",
               
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateJobRuleAPIView(BaseCompanyJobView):
    """API to create eligibility rules for a job."""
    
    @extend_schema(
        tags=['Dashboard - Company - Jobs'],
        description="Create Create Job Rule.",
        request=JobRuleCreateSerializer,
        responses={200: JobRuleCreateSerializer},
    )
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
                job=job,
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
                job=job,
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
    
    @extend_schema(tags=['Dashboard - Company - Jobs'], description="Partially update Update Job Rule.",
        responses={200: JobRuleUpdateSerializer},
    )
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
                    job=job,
               
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

        

            # 6. Validate logical consistency first
            new_rule_type = serializer.validated_data.get('rule_type')
            new_rule_type_id = serializer.validated_data.get('rule_type_id')

            # If rule_type is changing, rule_type_id MUST also be provided
            if new_rule_type and new_rule_type != job_rule.rule_type:
                if not new_rule_type_id:
                    return CustomResponse(
                        general_message="When changing rule_type, you must also provide rule_type_id",
                        message={"error_code": "MISSING_RULE_TYPE_ID"}
                    ).get_failure_response(
                        status_code=400,
                        http_status_code=status.HTTP_400_BAD_REQUEST
                    )

            # Get final values for duplicate check
            final_rule_type = new_rule_type or job_rule.rule_type
            final_rule_type_id = new_rule_type_id or job_rule.rule_type_id

            # Check for duplicates if anything is changing
            if (final_rule_type != job_rule.rule_type) or (final_rule_type_id != job_rule.rule_type_id):
                existing_rule = CompanyJobRule.objects.filter(
                    job=job,
                    rule_type=final_rule_type,
                    rule_type_id=final_rule_type_id,
                ).exclude(id=job_rule.id).first()
                
                if existing_rule:
                    return CustomResponse(
                        general_message=f"A rule with this {final_rule_type} already exists for the job",
                        message={"error_code": "DUPLICATE_RULE"}
                    ).get_failure_response(
                        status_code=400,
                        http_status_code=status.HTTP_400_BAD_REQUEST
                    )

            # 7. Update the job rule
            if new_rule_type:
               job_rule.rule_type = new_rule_type

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


class DeleteJobRuleAPIView(BaseCompanyJobView):
    """API to delete a specific job rule."""
    
    @extend_schema(tags=['Dashboard - Company - Jobs'], description="Delete Delete Job Rule.",
        responses={200: inline_serializer(
            name='JobDeleteJobRuleResponse',
            fields={
                'rule_id': s.CharField(),
                'job_id': s.CharField(),
                'deleted_at': s.CharField(),
            },
        )},
    )
    def delete(self, request, job_id, rule_id):
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
                job = CompanyJob.objects.get(id=job_id, is_deleted=False)
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

            # 4. Get the job rule to delete
            try:
                job_rule = CompanyJobRule.objects.get(
                    id=rule_id,
                    job=job
                )
            except CompanyJobRule.DoesNotExist:
                return CustomResponse(
                    general_message="Job rule does not exist",
                    message={"error_code": "RULE_NOT_FOUND"}
                ).get_failure_response(
                    status_code=404,
                    http_status_code=status.HTTP_404_NOT_FOUND
                )

            # 5. Hard delete the job rule
            job_rule.delete()
            
            # 6. Prepare response
            response_data = {
                "rule_id": str(rule_id),
                "job_id": str(job_id),
                "deleted_at": timezone.now().strftime('%Y-%m-%dT%H:%M:%SZ')
            }

            return CustomResponse(
                general_message="Job rule deleted successfully",
                response=response_data
            ).get_success_response()

        except Exception as e:
            print(f"Error deleting job rule: {str(e)}")
            return CustomResponse(
                general_message="Something went wrong",
                message={"error_code": "SERVER_ERROR"}
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PublicJobsListAPIView(APIView):
    """Public API to browse active jobs across all companies. No auth required."""
    permission_classes = []  # No authentication needed

    @extend_schema(
        tags=['Dashboard - Company - Jobs'],
        description="Retrieve Public Jobs List.",
        responses={200: CompanyJobListSerializer},
    )
    def get(self, request):
        jobs_qs = CompanyJob.objects.filter(
            is_deleted=False,
            status='Active'
        ).select_related('company_id').prefetch_related('rules').order_by('-created_at')

        paginated_data = CommonUtils.get_paginated_queryset(
            queryset=jobs_qs,
            request=request,
            search_fields=["title", "location", "job_type"],
            sort_fields={"title": "title", "createdAt": "created_at"},
            is_pagination=True
        )

        serializer = CompanyJobListSerializer(list(paginated_data["queryset"]), many=True)
        return CustomResponse(
            response={"jobs": serializer.data, "pagination": paginated_data["pagination"]},
            general_message="Jobs fetched successfully"
        ).get_success_response()
