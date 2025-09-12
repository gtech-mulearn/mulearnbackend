import uuid
import jwt
from datetime import timedelta
from decouple import config
from django.utils import timezone
from django.db.models import Sum, Max, Prefetch, F, OuterRef, Subquery, IntegerField, Count, Q, Prefetch
from rest_framework.views import APIView
from django.core.files.storage import FileSystemStorage
from decouple import config as decouple_config
from utils.permission import role_required
from utils.types import RoleType
from .serializers import (
    LaunchpadJobTaskSerializer, LaunchpadLeaderBoardSerializer, LaunchpadParticipantsSerializer, LaunchpadUserListSerializer,
    CollegeDataSerializer, LaunchpadUserSerializer, UserProfileUpdateSerializer,LaunchpadJobUpdateSerializer,
    LaunchpadUpdateUserSerializer, LaunchPadRankSerializer, TaskCompletedLeaderBoardSerializer, TaskVerificationSerializer, LaunchpadCompanyPublicSerializer,ForgotPasswordSerializer, ResetPasswordSerializer, ChangePasswordSerializer
)
from api.dashboard.profile.profile_serializer import (
    UserProfileSerializer, LinkSocials, UserLevelSerializer, UserLogSerializer,
)
from utils.response import CustomResponse
from utils.utils import CommonUtils, ImportCSV
from utils.types import LaunchPadLevels, LaunchPadRoles
from utils.permission import JWTUtils
from db.user import User, UserRoleLink, Role, Socials
from db.organization import UserOrganizationLink, Organization
from db.task import KarmaActivityLog, Level, TaskList, Wallet
from db.launchpad import LaunchPadUsers, LaunchPadUserCollegeLink, LaunchPad , LaunchpadJobApplications


from rest_framework import status
from db.launchpad import LaunchpadCompanies, LaunchpadRecruiters, LaunchpadJobs , LaunchpadJobTasks
from .serializers import LaunchpadCompaniesSerializer, LaunchpadRecruiterSerializer, LaunchpadJobsSerializer, EligibleStudentSerializer
from django.contrib.auth.hashers import make_password, check_password
from django.db import IntegrityError
from utils.permission import CustomizePermission
from utils.response import CustomResponse
from utils.launchpad_permission import LaunchpadJWTPermission
from typing import List
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
import decouple
import secrets


def send_template_mail(context: dict, subject: str, address: List[str], attachment: str = None):
    """
    Sends an email to a user with the provided context, subject, template address, and optional attachment.

    :param context: Dictionary containing user data and other relevant information.
    :param subject: Subject of the email.
    :param address: List of strings representing the path to the email template file.
    :param attachment: Optional attachment to send with the email.
    """
    from_mail = decouple.config("FROM_MAIL")
    base_url = decouple.config("FR_DOMAIN_NAME")

    email_content = render_to_string(
        f"mails/{'/'.join(map(str, address))}", {"user": context, "base_url": base_url}
    )
    mail = context.get("mails") or context.get("email")

    if attachment is None:
        send_mail(
            subject=subject,
            message=email_content,
            from_email=from_mail,
            recipient_list=[mail],
            html_message=email_content,
            fail_silently=False,
        )
    else:
        email = EmailMessage(
            subject=subject,
            body=email_content,
            from_email=from_mail,
            to=[mail],
        )
        email.attach(attachment)
        email.content_subtype = "html"
        email.send()
        

def get_current_utc_time():
    from django.utils import timezone
    return timezone.now()

def generate_launchpad_jwt(user, user_type):
    access_expiry_time = get_current_utc_time() + timedelta(hours=3)
    access_expiry = access_expiry_time.strftime("%Y-%m-%d %H:%M:%S%z")
    
    access_token = jwt.encode(
        {
            "id": user.id,
            "user_type": user_type,  # "company" or "recruiter"
            "expiry": access_expiry,
            "tokenType": "access",
        },
        config("SECRET_KEY"),
        algorithm="HS256",
    )
    
    refresh_expiry_time = get_current_utc_time() + timedelta(days=7)  # 7 days
    refresh_expiry = refresh_expiry_time.strftime("%Y-%m-%d %H:%M:%S%z")
    
    refresh_token = jwt.encode(
        {
            "id": user.id,
            "user_type": user_type,
            "expiry": refresh_expiry,
            "tokenType": "refresh",
        },
        config("SECRET_KEY"),
        algorithm="HS256",
    )
    return access_token, refresh_token


class RegisterCompanyAPI(APIView):
    def post(self, request):
        required_fields = ['name', 'username']
        for field in required_fields:
            if not request.data.get(field):
                return CustomResponse(
                    message={field: [f'{field} is required']},
                    general_message="Registration failed"
                ).get_failure_response()

        serializer = LaunchpadCompaniesSerializer(data={
            'id': str(uuid.uuid4()),
            'name': request.data.get('name'),
            'poc_name': request.data.get('poc_name'),
            'poc_role': request.data.get('poc_role'),
            'poc_email': request.data.get('poc_email'),
            'poc_phone': request.data.get('poc_phone') or None,
            'website': request.data.get('website') or None,
            'description': request.data.get('description') or None,
            'address': request.data.get('address') or None,
            'username': request.data.get('username'),
            'password': make_password(request.data.get('password'))
        })

        if serializer.is_valid():
            company = serializer.save()
            # Send registration success mail
            try:
                send_template_mail(
                    context={
                        "email": company.poc_email,
                        "full_name": company.name or company.poc_name,
                    },
                    subject="MuLearn Launchpad company registered successfully",
                    address=["launchpad-REG.html"]
                )
            except Exception as e:
                print(f"Error sending registration email: {e}")

            return CustomResponse(
                response={
                    'id': company.id,
                    'name': company.name,
                    'username': company.username,
                    'poc_name': company.poc_name,
                    'poc_email': company.poc_email,
                    'created_at': company.created_at
                },
                general_message="Company registered successfully"
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors,
            general_message="Registration failed"
        ).get_failure_response()

class CompanyListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
      companies = LaunchpadCompanies.objects.all()
      data = [
      {
        'id': company.id,
        'name': company.name,
        'poc_name': company.poc_name,
        'poc_email': company.poc_email,
        'poc_phone': company.poc_phone,
        'website': company.website,
        'description': company.description,
        'address': company.address,
        'is_verified': company.is_verified,
      } for company in companies
    ]
      return CustomResponse(
      response=data,
      general_message="Company list fetched successfully"
    ).get_success_response()

class CompanyListVerifiedAPI(APIView):
    def get(self, request):
        companies = LaunchpadCompanies.objects.filter(is_verified=True)

        if not companies.exists():
            return CustomResponse(
                general_message="No verified companies found."
            ).get_failure_response()

        serializer = LaunchpadCompanyPublicSerializer(companies, many=True)
        return CustomResponse(
            response=serializer.data,
            general_message="Verified company list fetched successfully"
        ).get_success_response()


class RegisterRecruiterAPI(APIView):
  authentication_classes = [LaunchpadJWTPermission]
  def post(self, request):
    print(request.auth)
    if request.auth["user_type"] != "company":
      return CustomResponse(general_message="Only companies can register recruiters.").get_failure_response()
    company = LaunchpadCompanies.objects.filter(id=request.auth["id"]).first()
    if company.is_verified is False:
      return CustomResponse(
        general_message="Company is not verified. Please contact admin."
      ).get_failure_response()

    serializer = LaunchpadRecruiterSerializer(data={
      'id': str(uuid.uuid4()),
      'company': company.id,
      'name': request.data.get('name'),
      'email': request.data.get('email'),
      'phone': request.data.get('phone'),
      'password': make_password(request.data.get('password')),
      'role': request.data.get('role')
    })
   
    if serializer.is_valid():
      try:
        recruiter = serializer.save()
        return CustomResponse(
          response={
            'id': recruiter.id,
            'name': recruiter.name,
            'email': recruiter.email,
            'phone': recruiter.phone,
            'role': recruiter.role,
            'company_id': recruiter.company_id,
            'created_at': recruiter.created_at
          },
          general_message="Recruiter registered successfully"
        ).get_success_response()
      except IntegrityError as e:
        if 'email' in str(e):
          return CustomResponse(
            message={'email': ['A recruiter with this email already exists.']},
            general_message="Signup failed"
          ).get_failure_response()
        else:
          return CustomResponse(
            message={'detail': ['Database error occurred.' + str(e)]},
            general_message="Signup failed"
          ).get_failure_response()

    return CustomResponse(
      message=serializer.errors,
      general_message="Signup failed"
    ).get_failure_response()
  
class AddJobAPI(APIView):
    authentication_classes = [LaunchpadJWTPermission]

    def post(self, request):
        if request.auth["user_type"] != "recruiter":
            return CustomResponse(general_message="Only recruiters can add jobs.").get_failure_response()
        recruiter_obj = LaunchpadRecruiters.objects.filter(id=request.auth["id"]).first()

        if request.data.get('opening_type') == "General":
            serializer = LaunchpadJobsSerializer(data={
                'id': str(uuid.uuid4()),
                'company': recruiter_obj.company_id,
                'recruiter': recruiter_obj.id,
                'title': request.data.get('title'),
                'skills': request.data.get('skills'),
                'experience': request.data.get('experience'),
                "minimum_karma": request.data.get('minimum_karma') or 0,
                'opening_type': request.data.get('opening_type') or "General",
                'location': request.data.get('location') or None,
                'salary_range': request.data.get('salary_range') or None,
                'job_type': request.data.get('job_type') or None,
                'domain': request.data.get('domain'),
                'interest_groups': request.data.get('interest_groups')
            })   
       
            if serializer.is_valid():
                try:
                    job = serializer.save()
                    response_data = {
                        'id': job.id,
                        'company_id': job.company_id,
                        'recruiter_id': job.recruiter_id,
                        'title': job.title,
                        'skills': job.skills or None,
                        'experience': job.experience or None,
                        'domain': job.domain,
                        'interest_groups': job.interest_groups,
                        'created_at': job.created_at
                    }
                    return CustomResponse(
                        response=response_data,
                        general_message="Job created successfully"
                    ).get_success_response()
                except IntegrityError as e:
                    return CustomResponse(
                        message={'detail': ['Database error occurred.' + str(e)]},
                        general_message="Job creation failed"
                    ).get_failure_response()
        elif request.data.get('opening_type') == "Task":
            if not request.data.get('task_description'):
                return CustomResponse(
                    message={'task_description': ['Task description is required for task-based openings.']},
                    general_message="Job creation failed"
                ).get_failure_response()
            
            task_serializer = LaunchpadJobTaskSerializer(data={
                'id': str(uuid.uuid4()),
                'task_description': request.data.get('task_description')
            })
            if not task_serializer.is_valid():
                return CustomResponse(
                    message=task_serializer.errors,
                    general_message="Job creation failed"
                ).get_failure_response()
            task = task_serializer.save()
            serializer = LaunchpadJobsSerializer(data={
                'id': str(uuid.uuid4()),
                'company': recruiter_obj.company_id,
                'recruiter': recruiter_obj.id,
                'title': request.data.get('title'),
                'skills': request.data.get('skills'),
                'experience': request.data.get('experience') or None,
                "minimum_karma": request.data.get('minimum_karma') or 0,
                'opening_type': request.data.get('opening_type') or "Task",
                'location': request.data.get('location') or None,
                'salary_range': request.data.get('salary_range') or None,
                'job_type': request.data.get('job_type') or None,
                'domain': request.data.get('domain'),
                'interest_groups': request.data.get('interest_groups'),
                'task': task.id
            })

            if serializer.is_valid():
                try:
                    job = serializer.save()
                    response_data = {
                        'id': job.id,
                        'company_id': job.company_id,
                        'recruiter_id': job.recruiter_id,
                        'title': job.title,
                        'skills': job.skills or None,
                        'experience': job.experience or None,
                        'domain': job.domain,
                        'interest_groups': job.interest_groups,
                        'task_id': job.task.id if job.task else None,
                        'task': job.task.task_description if job.task else None,
                        'created_at': job.created_at
                    }
                    return CustomResponse(
                        response=response_data,
                        general_message="Job created successfully"
                    ).get_success_response()
                except IntegrityError as e:
                    return CustomResponse(
                        message={'detail': ['Database error occurred.' + str(e)]},
                        general_message="Job creation failed"
                    ).get_failure_response()
               
        return CustomResponse(
            message=serializer.errors,
            general_message="Job creation failed"
        ).get_failure_response()

class JobAPI(APIView):
    authentication_classes = [LaunchpadJWTPermission]
    def get(self, request, job_id):
        user_type = request.auth["user_type"]
        user_id = request.auth["id"]
        
        try:
            job = LaunchpadJobs.objects.prefetch_related(
                Prefetch('task', queryset=LaunchpadJobTasks.objects.all())
            ).select_related('company', 'recruiter').get(id=job_id)
            if user_type == "recruiter" and job.recruiter_id != user_id:
                return CustomResponse(
                    general_message="You can only view your own jobs."
                ).get_failure_response()
            elif user_type == "company" and job.company_id != user_id:
                return CustomResponse(
                    general_message="You can only view jobs posted by your company."
                ).get_failure_response()
            
            response_data = {
                'id': job.id,
                'company_id': job.company_id,
                'recruiter_id': job.recruiter_id,
                'title': job.title,
                'skills': job.skills or None,
                'experience': job.experience or None,
                'domain': job.domain,
                'interest_groups': job.interest_groups,
                'opening_type': job.opening_type,
                'location': job.location or None,
                'salary_range': job.salary_range or None,
                'job_type': job.job_type or None,
                'minimum_karma': job.minimum_karma,
                'created_at': job.created_at,
                'updated_at': job.updated_at
            }
            
            if job.opening_type == "Task":
                response_data['task'] = {
                    'id': job.task.id if job.task else None,
                    'task_description': job.task.task_description if job.task else None,
                    'hashtags': job.task.hashtags if job.task else None,
                    'is_verified': job.task.is_verified if job.task else False
                }
            else:
                response_data['task'] = None
            
            return CustomResponse(
                response=response_data,
                general_message="Job details fetched successfully"
            ).get_success_response()
        
        except LaunchpadJobs.DoesNotExist:
            return CustomResponse(
                general_message="Job not found."
            ).get_failure_response()
        
    def put(self, request, job_id):
        user_type = request.auth["user_type"]
        user_id = request.auth["id"]
        
        if user_type not in ["recruiter", "company"]:
            return CustomResponse(
                general_message="Only recruiters and companies can update jobs."
            ).get_failure_response()
        
        try:
            job = LaunchpadJobs.objects.prefetch_related(
                Prefetch('task', queryset=LaunchpadJobTasks.objects.all())
            ).select_related('company', 'recruiter').get(id=job_id)
            # Check permissions
            if user_type == "recruiter" and job.recruiter_id != user_id:
                return CustomResponse(
                    general_message="You can only update your own jobs."
                ).get_failure_response()
            elif user_type == "company" and job.company_id != user_id:
                return CustomResponse(
                    general_message="You can only update jobs posted by your company."
                ).get_failure_response()
            
            # Update job using serializer
            serializer = LaunchpadJobUpdateSerializer(job, data=request.data, partial=True)
            
            if serializer.is_valid():
                updated_job = serializer.save()
                
                # Prepare response
                response_data = {
                    'id': updated_job.id,
                    'title': updated_job.title,
                    'company_id': updated_job.company_id,
                    'recruiter_id': updated_job.recruiter_id,
                    'skills': updated_job.skills,
                    'experience': updated_job.experience,
                    'minimum_karma': updated_job.minimum_karma,
                    'opening_type': updated_job.opening_type,
                    'location': updated_job.location,
                    'salary_range': updated_job.salary_range,
                    'job_type': updated_job.job_type,
                    'domain': updated_job.domain,
                    'interest_groups': updated_job.interest_groups,
                    'updated_at': updated_job.updated_at
                }
                
                # Add task info if it's a task job
                if updated_job.opening_type == "Task" and updated_job.task:
                    response_data['task'] = {
                        'id': updated_job.task.id,
                        'task_description': updated_job.task.task_description,
                        'hashtags': updated_job.task.hashtags,
                        'is_verified': updated_job.task.is_verified
                    }
                else:
                    response_data['task'] = None
                
                return CustomResponse(
                    response=response_data,
                    general_message="Job updated successfully"
                ).get_success_response()
            
            return CustomResponse(
                message=serializer.errors,
                general_message="Job update failed"
            ).get_failure_response()
            
        except LaunchpadJobs.DoesNotExist:
            return CustomResponse(
                general_message="Job not found."
            ).get_failure_response()
        except Exception as e:
            return CustomResponse(
                message={'detail': [str(e)]},
                general_message="Job update failed"
            ).get_failure_response()
        
    def delete(self, request, job_id):
        user_type = request.auth["user_type"]
        user_id = request.auth["id"]
        
        if user_type not in ["recruiter", "company"]:
            return CustomResponse(
                general_message="Only recruiters and companies can delete jobs."
            ).get_failure_response()
        
        try:
            job = LaunchpadJobs.objects.get(id=job_id)
            
            # Check permissions
            if user_type == "recruiter" and job.recruiter_id != user_id:
                return CustomResponse(
                    general_message="You can only delete your own jobs."
                ).get_failure_response()
            elif user_type == "company" and job.company_id != user_id:
                return CustomResponse(
                    general_message="You can only delete jobs posted by your company."
                ).get_failure_response()
            
            job.delete()
            return CustomResponse(
                general_message="Job deleted successfully"
            ).get_success_response()
        
        except LaunchpadJobs.DoesNotExist:
            return CustomResponse(
                general_message="Job not found."
            ).get_failure_response()
        
class ListJobsAPI(APIView):
    authentication_classes = [CustomizePermission, LaunchpadJWTPermission]
    
    def get(self, request):
        user_type = request.auth.get("user_type")
        user_id = request.auth.get("id")
        
        jobs_query = LaunchpadJobs.objects.prefetch_related(
            Prefetch('task', queryset=LaunchpadJobTasks.objects.all())
        ).select_related('company', 'recruiter')
        
        if user_type == "recruiter":
            try:
                recruiter = LaunchpadRecruiters.objects.get(id=user_id)
                jobs = jobs_query.filter(company_id=recruiter.company_id)
            except LaunchpadRecruiters.DoesNotExist:
                return CustomResponse(general_message="Recruiter not found.").get_failure_response()
        elif user_type == "company":
            jobs = jobs_query.filter(company_id=user_id)
        else:
            jobs = jobs_query.all()
        
        data = []
        for job in jobs:
            job_data = {
                'id': job.id,
                'company_id': job.company_id,
                'company_name': job.company.name if job.company else None,
                'recruiter_id': job.recruiter_id,
                'recruiter_name': job.recruiter.name if job.recruiter else None,
                'title': job.title,
                'skills': job.skills or None,
                'experience': job.experience or None,
                'domain': job.domain,
                'interest_groups': job.interest_groups,
                'opening_type': job.opening_type,
                'location': job.location or None,
                'salary_range': job.salary_range or None,
                'job_type': job.job_type or None,
                'minimum_karma': job.minimum_karma,
                'created_at': job.created_at,
                'updated_at': job.updated_at,
                'posted_by_current_recruiter': job.recruiter_id == user_id if user_type == "recruiter" else None
            }
            
            if job.opening_type == "Task":
                job_data['task_id'] = getattr(job.task, 'id', None) if hasattr(job, 'task') and job.task else None
                job_data['task_description'] = getattr(job.task, 'task_description', None) if hasattr(job, 'task') and job.task else None
                job_data['task_hashtag'] = getattr(job.task, 'hashtags', None) if hasattr(job, 'task') and job.task else None
                job_data['task_verified'] = getattr(job.task, 'is_verified', False) if hasattr(job, 'task') and job.task else False
            
            data.append(job_data)
        
        if user_type == "recruiter":
            try:
                recruiter = LaunchpadRecruiters.objects.get(id=user_id)
                company_name = recruiter.company.name if recruiter.company else "Unknown Company"
                total_company_jobs = len(data)
                own_jobs = len([job for job in data if job['recruiter_id'] == user_id])
                other_recruiters_jobs = total_company_jobs - own_jobs
            except LaunchpadRecruiters.DoesNotExist:
                company_name = "Unknown Company"
                own_jobs = 0
                other_recruiters_jobs = 0
                
            summary = {
                'total_jobs': len(data),
                'general_jobs': len([job for job in data if job['opening_type'] == 'General']),
                'task_jobs': len([job for job in data if job['opening_type'] == 'Task']),
                'own_jobs': own_jobs,
                'other_recruiters_jobs': other_recruiters_jobs,
                'company_name': company_name,
                'user_type': user_type,
                'user_id': user_id
            }
        else:
            summary = {
                'total_jobs': len(data),
                'general_jobs': len([job for job in data if job['opening_type'] == 'General']),
                'task_jobs': len([job for job in data if job['opening_type'] == 'Task']),
                'user_type': user_type,
                'user_id': user_id
            }
        
        return CustomResponse(
            response={
                'jobs': data,
                'summary': summary
            },
            general_message="Job list fetched successfully"
        ).get_success_response()

class VerifyTaskAPI(APIView):
    authentication_classes = [CustomizePermission]
    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        serializer = TaskVerificationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors,
                general_message="Validation failed"
            ).get_failure_response()
        
        try:
            task = serializer.save()
            return CustomResponse(response={
                "task_id": task.id,
                "task_description": task.task_description,
                "hashtag": task.hashtags,
                "is_verified": task.is_verified,
                "message": "Task verified successfully."
            }).get_success_response()
            
        except Exception as e:
            return CustomResponse(
                message={'detail': [str(e)]},
                general_message="Task verification failed"
            ).get_failure_response()

class LoginCompanyAPI(APIView):
    def post(self, request):
        data = request.data
        usernameOrEmail = data.get("username") or data.get("email")
        password = data.get("password")
        if not usernameOrEmail or not password:
            return CustomResponse(general_message="Username/email and password are required.").get_failure_response()
        
        company = None
        try:
            company = LaunchpadCompanies.objects.get(username=usernameOrEmail)
        except LaunchpadCompanies.DoesNotExist:
            try:
                company = LaunchpadCompanies.objects.get(poc_email=usernameOrEmail)
            except LaunchpadCompanies.DoesNotExist:
                return CustomResponse(general_message="Invalid credentials.").get_failure_response()
        
        if not check_password(password, company.password):
            return CustomResponse(general_message="Invalid credentials.").get_failure_response()
        if company.is_verified is False:
            return CustomResponse(general_message="Company is not verified.").get_failure_response()
        access_token, refresh_token = generate_launchpad_jwt(company, "company")
        
        return CustomResponse(response={
            'id': company.id,
            'name': company.name,
            'username': company.username,
            'poc_name': company.poc_name,
            'poc_email': company.poc_email,
            'created_at': company.created_at,
            'accessToken': access_token,
            'refreshToken': refresh_token
        }).get_success_response()

class LoginRecruiterAPI(APIView):
    def post(self, request):
        data = request.data
        emailOrPhone = data.get('email') or data.get('phone')
        password = data.get("password")
        if not emailOrPhone or not password:
            return CustomResponse(general_message="Email/phone and password are required.").get_failure_response()
        
        recruiter = None
        try:
            recruiter = LaunchpadRecruiters.objects.get(email=emailOrPhone)
        except LaunchpadRecruiters.DoesNotExist:
            try:
                recruiter = LaunchpadRecruiters.objects.get(phone=emailOrPhone)
            except LaunchpadRecruiters.DoesNotExist:
                return CustomResponse(general_message="Invalid credentials.").get_failure_response()
        
        if not check_password(password, recruiter.password):
            return CustomResponse(general_message="Invalid credentials.").get_failure_response()
        
        if not recruiter.company.is_verified:
            return CustomResponse(
                general_message="Account does not exist"
            ).get_failure_response()
        
        access_token, refresh_token = generate_launchpad_jwt(recruiter, "recruiter")
        
        return CustomResponse(response={
            'id': recruiter.id,
            'name': recruiter.name,
            'email': recruiter.email,
            'phone': recruiter.phone,
            'role': recruiter.role,
            'company_id': recruiter.company_id,
            'created_at': recruiter.created_at,
            'accessToken': access_token,
            'refreshToken': refresh_token
        }).get_success_response()

class GetCompanyInfoAPI(APIView):
    def post(self, request):
        company_id = request.data.get('company_id')
        if not company_id:
            return CustomResponse(general_message="Company ID is required.").get_failure_response()
        
        try:
            company = LaunchpadCompanies.objects.get(id=company_id)
            return CustomResponse(response={
                'id': company.id,
                'name': company.name,
                'username': company.username,
                'poc_name': company.poc_name,
                'poc_role': company.poc_role,
                'poc_email': company.poc_email,
                'poc_phone': company.poc_phone,
                'website': company.website,
                'description': company.description,
                'address': company.address,
                'is_verified': company.is_verified,
                'created_at': company.created_at,
                'updated_at': company.updated_at,
                'recruiters': [
                    {
                        'id': recruiter.id,
                        'name': recruiter.name,
                        'email': recruiter.email,
                        'phone': recruiter.phone,
                        'role': recruiter.role,
                        'created_at': recruiter.created_at,
                        'updated_at': recruiter.updated_at
                    }
                    for recruiter in LaunchpadRecruiters.objects.filter(company=company)
                ]

            }).get_success_response()
        except LaunchpadCompanies.DoesNotExist:
            return CustomResponse(general_message="Company not found.").get_failure_response()

class GetRecruiterInfoAPI(APIView):
    def post(self, request):
        recruiter_id = request.data.get('recruiter_id')
        if not recruiter_id:
            return CustomResponse(general_message="Recruiter ID is required.").get_failure_response()
        
        try:
            recruiter = LaunchpadRecruiters.objects.select_related('company').get(id=recruiter_id)
            return CustomResponse(response={
                'id': recruiter.id,
                'name': recruiter.name,
                'email': recruiter.email,
                'phone': recruiter.phone,
                'role': recruiter.role,
                'company_id': recruiter.company_id,
                'company_name': recruiter.company.name if recruiter.company else None,
                'created_at': recruiter.created_at,
                'updated_at': recruiter.updated_at
            }).get_success_response()
        except LaunchpadRecruiters.DoesNotExist:
            return CustomResponse(general_message="Recruiter not found.").get_failure_response()


class RefreshTokenAPI(APIView):
    def post(self, request):
        refresh_token = request.data.get("refreshToken")
        if not refresh_token:
            return CustomResponse(general_message="Refresh token is required.").get_failure_response()
        
        try:
            payload = jwt.decode(
                refresh_token,
                config("SECRET_KEY"),
                algorithms=["HS256"],
                verify=True,
            )
        except jwt.ExpiredSignatureError:
            return CustomResponse(general_message="Refresh token has expired.").get_failure_response()
        except jwt.InvalidTokenError:
            return CustomResponse(general_message="Invalid refresh token.").get_failure_response()
        
        user_id = payload.get("id")
        user_type = payload.get("user_type")
        token_type = payload.get("tokenType")
        
        if token_type != "refresh":
            return CustomResponse(general_message="Invalid token type.").get_failure_response()

        user = None
        if user_type == "company":
            try:
                user = LaunchpadCompanies.objects.get(id=user_id)
            except LaunchpadCompanies.DoesNotExist:
                return CustomResponse(general_message="Company not found.").get_failure_response()
        elif user_type == "recruiter":
            try:
                user = LaunchpadRecruiters.objects.get(id=user_id)
            except LaunchpadRecruiters.DoesNotExist:
                return CustomResponse(general_message="Recruiter not found.").get_failure_response()
        else:
            return CustomResponse(general_message="Invalid user type.").get_failure_response()
        
        # Generate new tokens
        access_token, new_refresh_token = generate_launchpad_jwt(user, user_type)
        
        return CustomResponse(response={
            "accessToken": access_token,
            "refreshToken": new_refresh_token
        }).get_success_response()


class CompanyVerifyAPI(APIView):
    authentication_classes = [CustomizePermission]
    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        company_id = request.data.get('company_id')
        if not company_id:
            return CustomResponse(general_message="Company ID is required.").get_failure_response()

        try:
            company = LaunchpadCompanies.objects.get(id=company_id)
            company.is_verified = True
            company.save()

            # Send verification success mail
            try:
                send_template_mail(
                    context={
                        "email": company.poc_email,
                        "full_name": company.name or company.poc_name,
                    },
                    subject="Company Verified - Launchpad",
                    address=["launchpad-VFY.html"]
                )
            except Exception as e:
                # Optionally log error, but don't fail verification
                pass

            return CustomResponse(response={
                "company_name": company.name,
                "message": f"{company.name} verified successfully."
            }).get_success_response()

        except LaunchpadCompanies.DoesNotExist:
            return CustomResponse(general_message="Company not found.").get_failure_response()


class ListLaunchpadStudentsAPI(APIView):
    authentication_classes = [LaunchpadJWTPermission]

    def get(self, request, job_id):
        user_type = request.auth["user_type"]
        if user_type not in ["recruiter", "company"]:
            return CustomResponse(
                general_message="Only recruiters and companies can view eligible students.").get_failure_response()

        try:
            job = LaunchpadJobs.objects.get(id=job_id)
            user_id = request.auth["id"]

            if user_type == "recruiter" and job.recruiter_id != user_id:
                return CustomResponse(
                    general_message="You can only view students for your own jobs.").get_failure_response()
            elif user_type == "company" and job.recruiter.company_id != user_id:
                return CustomResponse(
                    general_message="You can only view students for jobs posted by your company.").get_failure_response()

        except LaunchpadJobs.DoesNotExist:
            return CustomResponse(general_message="Job not found.").get_failure_response()
        except AttributeError:
            return CustomResponse(general_message="Invalid job or user relationship.").get_failure_response()

        # Get all applications for this job with more details
        job_applications = LaunchpadJobApplications.objects.filter(
            job=job
        ).values(
            'id', 'student_id', 'status', 'applied_at', 'invited_at',
            'resume_link', 'linkedin_link', 'portfolio_link',
            'cover_letter', 'other_link'
        )

        # Create a dictionary for quick lookup of application status and links
        application_status_map = {
            app['student_id']: {
                'application_id': app['id'],
                'status': app['status'],
                'applied_at': app['applied_at'],
                'invited_at': app['invited_at'],
                'resume_link': app['resume_link'],
                'linkedin_link': app['linkedin_link'],
                'portfolio_link': app['portfolio_link'],
                'cover_letter': app['cover_letter'],
                'other_link': app['other_link']
            }
            for app in job_applications
        }

        if job.opening_type == "Task":
            try:
                # Get the job task to fetch hashtag
                job_task = LaunchpadJobTasks.objects.get(id=job.task_id)
                hashtag = job_task.hashtags

                # Get matching TaskList IDs with the same hashtag
                matching_tasks = TaskList.objects.filter(hashtag=hashtag).values_list('id', flat=True)

                if not matching_tasks:
                    return CustomResponse(
                        general_message="No matching tasks found for this job's hashtag."
                    ).get_failure_response()

                # Get users who completed any of the matching tasks
                task_completers = KarmaActivityLog.objects.filter(
                    task_id__in=matching_tasks
                ).values('user_id').distinct()

                # Calculate ranks based on total karma from all matching tasks
                task_karma_ranks = (
                    KarmaActivityLog.objects.filter(
                        task_id__in=matching_tasks
                    )
                    .values('user_id')
                    .annotate(total_karma=Sum('karma'))
                    .order_by("-total_karma", "-created_at")
                )

                ranks = {user["user_id"]: i + 1 for i, user in enumerate(task_karma_ranks)}

                eligible_students = User.objects.filter(
                    id__in=[user['user_id'] for user in task_completers],
                    interested_in_work=True
                ).select_related(
                    'wallet_user', 'user_lvl_link_user__level'
                ).prefetch_related(
                    'user_ig_link_user__ig',
                    'user_organization_link_user__org',
                    'user_role_link_user__role'
                ).distinct().annotate(
                    user_id=F("id"),
                    karma=F("wallet_user__karma"),
                    level=F("user_lvl_link_user__level__name"),
                )

                user_karma_map = {user['user_id']: user['total_karma'] for user in task_karma_ranks}
                eligible_students = sorted(
                    eligible_students,
                    key=lambda x: (-user_karma_map.get(x.id, 0), x.id)
                )

            except LaunchpadJobTasks.DoesNotExist:
                return CustomResponse(general_message="Job task not found.").get_failure_response()
            except Exception as e:
                return CustomResponse(general_message=str(e)).get_failure_response()

        else:

            rank = (
                Wallet.objects.filter(
                    user__interested_in_work=True,
                    karma__gte=job.minimum_karma
                )
                .order_by("-karma", "-updated_at", "created_at")
                .values(
                    "user_id",
                    "karma",
                )
            )

            ranks = {user["user_id"]: i + 1 for i, user in enumerate(rank)}

            eligible_students = User.objects.filter(
                interested_in_work=True,
                wallet_user__karma__gte=job.minimum_karma
            ).select_related(
                'wallet_user', 'user_lvl_link_user__level'
            ).prefetch_related(
                'user_ig_link_user__ig',
                'user_organization_link_user__org',
                'user_role_link_user__role'
            ).distinct().annotate(
                user_id=F("id"),
                karma=F("wallet_user__karma"),
                level=F("user_lvl_link_user__level__name"),
            )

            if job.interest_groups:
                interest_groups = [ig.strip() for ig in job.interest_groups.split(',')]
                eligible_students = eligible_students.filter(
                    user_ig_link_user__ig__name__in=interest_groups
                ).distinct()

            eligible_students = eligible_students.order_by('-karma', '-wallet_user__updated_at',
                                                           'wallet_user__created_at')

        paginated_queryset = CommonUtils.get_paginated_queryset(
            eligible_students,
            request,
            ["full_name", "level"],
            {
                "full_name": "full_name",
                "muid": "muid",
                "karma": "wallet_user__karma",
                "level": "user_lvl_link_user__level__level_order",
            },
        )

        serializer = EligibleStudentSerializer(
            paginated_queryset.get("queryset"),
            many=True,
            context={
                "ranks": ranks,
                "job": job,
                "application_status_map": application_status_map
            }
        )

        return CustomResponse(
            response={
                'job_info': {
                    'id': job.id,
                    'title': job.title,
                    'minimum_karma': job.minimum_karma,
                    'domain': job.domain,
                    'interest_groups': job.interest_groups,
                    'opening_type': job.opening_type,
                    'task_id': job.task_id if job.opening_type == "Task" else None
                },
                'data': serializer.data,
                'pagination': paginated_queryset.get("pagination"),
            },
            general_message="Eligible students fetched successfully"
        ).get_success_response()
    
class HireRequestsAPI(APIView):
    authentication_classes = [LaunchpadJWTPermission]
    
    def get(self, request):
        user_type = request.auth["user_type"]
        if user_type not in ["recruiter", "company"]:
            return CustomResponse(
                general_message="Only recruiters and companies can view hire requests."
            ).get_failure_response()
        
        user_id = request.auth["id"]
        job_id = request.query_params.get('job_id', None)
        status_filter = request.query_params.get('status', None)
        
        # Base query for applications
        applications = LaunchpadJobApplications.objects.select_related(
            'job', 'job__company', 'job__recruiter', 'student', 'student__wallet_user'
        ).prefetch_related(
            'student__user_organization_link_user__org',
            'student__user_ig_link_user__ig',
            'student__user_role_link_user__role'
        )
        
        # Filter by user type
        if user_type == "recruiter":
            applications = applications.filter(job__recruiter_id=user_id)
        elif user_type == "company":
            applications = applications.filter(job__company_id=user_id)
        
        # Filter by specific job if provided
        if job_id:
            try:
                if user_type == "recruiter":
                    job = LaunchpadJobs.objects.get(id=job_id, recruiter_id=user_id)
                else:  # company
                    job = LaunchpadJobs.objects.get(id=job_id, company_id=user_id)
                applications = applications.filter(job_id=job_id)
            except LaunchpadJobs.DoesNotExist:
                return CustomResponse(
                    general_message="Job not found or unauthorized."
                ).get_failure_response()
        
        # Apply status filter if provided
        if status_filter:
            valid_statuses = ['invited', 'applied', 'interview_scheduled', 'accepted', 'rejected']
            if status_filter not in valid_statuses:
                return CustomResponse(
                    general_message=f"Invalid status. Valid statuses: {', '.join(valid_statuses)}"
                ).get_failure_response()
            applications = applications.filter(status=status_filter)
        
        # Apply pagination
        paginated_queryset = CommonUtils.get_paginated_queryset(
            applications,
            request,
            ["student__full_name", "job__title", "job__company__name", "status"],
            {
                "student_name": "student__full_name",
                "student_email": "student__email",
                "student_muid": "student__muid",
                "job_title": "job__title",
                "company_name": "job__company__name",
                "recruiter_name": "job__recruiter__name",
                "karma": "student__wallet_user__karma",
                "status": "status",
                "invited_at": "invited_at",
                "applied_at": "applied_at",
            },
        )
        
        data = []
        for application in paginated_queryset.get("queryset"):
            student = application.student
            job = application.job
            
            # Get student's college info
            college_link = student.user_organization_link_user.filter(
                org__org_type='College'
            ).first()
            
            # Get student's interest groups
            interest_groups = [
                {
                    'id': ig_link.ig.id,
                    'name': ig_link.ig.name
                }
                for ig_link in student.user_ig_link_user.all()
            ]
            
            # Get student's roles
            roles = [
                {
                    'id': role_link.role.id,
                    'title': role_link.role.title
                }
                for role_link in student.user_role_link_user.filter(verified=True)
            ]
            
            # Get student's karma distribution
            karma_distribution = list(
                KarmaActivityLog.objects.filter(
                    user=student, 
                    appraiser_approved=True
                ).values(
                    task_type=F('task__type__title')
                ).annotate(
                    karma=Sum('karma')
                ).order_by('-karma')
            )
            
            # Calculate student's rank
            rank = Wallet.objects.filter(
                user__interested_in_work=True,
                karma__gt=student.wallet_user.karma if student.wallet_user else 0
            ).count() + 1
            
            application_data = {
                'application_id': application.id,
                'status': application.status,
                'timeline': {
                    'invited_at': application.invited_at,
                    'applied_at': application.applied_at,
                    'updated_at': application.updated_at
                },
                'student_info': {
                    'id': student.id,
                    'full_name': student.full_name,
                    'email': student.email,
                    'muid': student.muid,
                    'profile_pic': student.profile_pic,
                    'karma': student.wallet_user.karma if student.wallet_user else 0,
                    'rank': rank,
                    'level': student.user_lvl_link_user.level.name if hasattr(student, 'user_lvl_link_user') and student.user_lvl_link_user else None,
                    'interested_in_work': student.interested_in_work,
                    'college_name': college_link.org.title if college_link else None,
                    'college_district': college_link.org.district.name if college_link and college_link.org.district else None,
                    'college_state': college_link.org.district.zone.state.name if college_link and college_link.org.district and college_link.org.district.zone else None,
                    'interest_groups': interest_groups,
                    'roles': roles,
                    'karma_distribution': karma_distribution,
                    'created_at': student.created_at,
                    'last_active': student.last_active if hasattr(student, 'last_active') else None
                },
                'job_info': {
                    'id': job.id,
                    'title': job.title,
                    'company_name': job.company.name,
                    'company_id': job.company_id,
                    'recruiter_name': job.recruiter.name,
                    'recruiter_id': job.recruiter_id,
                    'recruiter_email': job.recruiter.email,
                    'recruiter_phone': job.recruiter.phone,
                    'opening_type': job.opening_type,
                    'domain': job.domain,
                    'skills': job.skills,
                    'experience': job.experience,
                    'location': job.location,
                    'salary_range': job.salary_range,
                    'job_type': job.job_type,
                    'minimum_karma': job.minimum_karma,
                    'interest_groups': job.interest_groups,
                    'created_at': job.created_at,
                    'updated_at': job.updated_at
                },
                'application_details': {
                    'resume_link': application.resume_link,
                    'linkedin_link': application.linkedin_link,
                    'portfolio_link': application.portfolio_link,
                    'cover_letter': application.cover_letter,
                    'other_link': application.other_link,
                    'links_available': bool(
                        application.resume_link or 
                        application.linkedin_link or 
                        application.portfolio_link or 
                        application.cover_letter or 
                        application.other_link
                    )
                } if application.status != 'invited' else None
            }
            
            # Add interview details if scheduled
            if application.status == 'interview_scheduled':
                application_data['interview_details'] = {
                    'interview_date': getattr(application, 'interview_date', None),
                    'interview_time': getattr(application, 'interview_time', None),
                    'interview_platform': getattr(application, 'interview_platform', None),
                    'interview_link': getattr(application, 'interview_link', None),
                    'interview_scheduled_at': application.updated_at
                }
            
            # Add task info if task-based job
            if job.opening_type == "Task" and job.task:
                application_data['task_info'] = {
                    'task_id': job.task.id,
                    'task_description': job.task.task_description,
                    'task_verified': job.task.is_verified,
                    'task_hashtag': job.task.hashtags
                }
            
            data.append(application_data)
        
        # Prepare summary statistics
        total_applications = applications.count()
        
        if job_id:
            # Stats for specific job
            summary_stats = {
                'job_id': job_id,
                'job_title': job.title,
                'company_name': job.company.name,
                'recruiter_name': job.recruiter.name,
                'total_applications': total_applications,
                'invited': applications.filter(status='invited').count(),
                'applied': applications.filter(status='applied').count(),
                'interview_scheduled': applications.filter(status='interview_scheduled').count(),
                'accepted': applications.filter(status='accepted').count(),
                'rejected': applications.filter(status='rejected').count(),
                'withdrawn': applications.filter(status='withdrawn').count(),
                'filtered_count': len(data),
                'filter_applied': {
                    'job_id': job_id,
                    'status': status_filter
                }
            }
        else:
            # Overall stats for user
            if user_type == "recruiter":
                recruiter = LaunchpadRecruiters.objects.get(id=user_id)
                user_jobs = LaunchpadJobs.objects.filter(recruiter_id=user_id)
                user_name = recruiter.name
                company_name = recruiter.company.name if recruiter.company else None
            else:  # company
                company = LaunchpadCompanies.objects.get(id=user_id)
                user_jobs = LaunchpadJobs.objects.filter(company_id=user_id)
                user_name = company.name
                company_name = company.name
            
            summary_stats = {
                'user_type': user_type,
                'user_name': user_name,
                'company_name': company_name,
                'total_jobs': user_jobs.count(),
                'total_applications': total_applications,
                'invited': applications.filter(status='invited').count(),
                'applied': applications.filter(status='applied').count(),
                'interview_scheduled': applications.filter(status='interview_scheduled').count(),
                'accepted': applications.filter(status='accepted').count(),
                'rejected': applications.filter(status='rejected').count(),
                'withdrawn': applications.filter(status='withdrawn').count(),
                'filtered_count': len(data),
                'filter_applied': {
                    'status': status_filter
                },
                'recent_activity': {
                    'applications_this_week': applications.filter(
                        applied_at__gte=timezone.now() - timedelta(days=7)
                    ).count(),
                    'interviews_this_week': applications.filter(
                        status='interview_scheduled',
                        updated_at__gte=timezone.now() - timedelta(days=7)
                    ).count()
                }
            }
        
        return CustomResponse().paginated_response(
            data={
                'hire_requests': data,
                'summary': summary_stats,
                'current_filters': {
                    'job_id': job_id,
                    'status': status_filter
                }
            },
            pagination=paginated_queryset.get("pagination")
        )

class SendJobInvitationsAPI(APIView):
    authentication_classes = [LaunchpadJWTPermission]
    
    def post(self, request):
        if request.auth["user_type"] != "recruiter":
            return CustomResponse(general_message="Only recruiters can send invitations.").get_failure_response()
        
        try:
            job_id = request.data.get('job_id')
            if not job_id:
                return CustomResponse(general_message="Job ID is required.").get_failure_response()
            job = LaunchpadJobs.objects.get(id=job_id)
            recruiter_id = request.auth["id"]
            
            # Ensure recruiter owns this job
            if job.recruiter_id != recruiter_id:
                return CustomResponse(general_message="You can only send invitations for your own jobs.").get_failure_response()
                
        except LaunchpadJobs.DoesNotExist:
            return CustomResponse(general_message="Job not found.").get_failure_response()
        
        student_ids = request.data.get('student_ids', [])
        
        if not student_ids:
            return CustomResponse(general_message="Please provide student IDs to invite.").get_failure_response()
        
        if not isinstance(student_ids, list):
            return CustomResponse(general_message="student_ids must be a list.").get_failure_response()
        
        # Verify students exist and are eligible
        eligible_students = User.objects.filter(
            id__in=student_ids,
            wallet_user__karma__gte=job.minimum_karma,
            interested_in_work=True
        )
        
        if len(eligible_students) != len(student_ids):
            invalid_students = set(student_ids) - set(eligible_students.values_list('id', flat=True))
            return CustomResponse(
                message={'invalid_students': list(invalid_students)},
                general_message="Some students are not eligible for this job."
            ).get_failure_response()
        
        # Create invitation records
        invitations = []
        already_invited = []
        
        for student in eligible_students:
            existing_invitation = LaunchpadJobApplications.objects.filter(
                job=job, student=student
            ).first()
            
            if existing_invitation:
                already_invited.append({
                    'student_id': student.id,
                    'student_name': student.full_name,
                    'current_status': existing_invitation.status
                })
            else:
                invitation = LaunchpadJobApplications(
                    id=str(uuid.uuid4()),
                    job=job,
                    student=student,
                    status='invited',
                    invited_at=timezone.now()
                )
                invitations.append(invitation)
        
        # Bulk create invitations
        if invitations:
            LaunchpadJobApplications.objects.bulk_create(invitations)
        
        # Prepare response data
        invited_students = [
            {
                'student_id': inv.student.id,
                'student_name': inv.student.full_name,
                'student_email': inv.student.email,
                'student_karma': inv.student.wallet_user.karma if inv.student.wallet_user else 0
            }
            for inv in invitations
        ]
        
        return CustomResponse(
            response={
                'job_info': {
                    'id': job.id,
                    'title': job.title,
                    'company_name': job.company.name if job.company else None
                },
                'invitation_summary': {
                    'total_requested': len(student_ids),
                    'successfully_invited': len(invitations),
                    'already_invited': len(already_invited)
                },
                'invited_students': invited_students,
                'already_invited_students': already_invited
            },
            general_message=f"Successfully sent {len(invitations)} job invitations"
        ).get_success_response()
    
class StudentJobInvitationsAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    def get(self, request):
        user_id = request.auth["id"]
        status_filter = request.query_params.get('status', None)  
        
        invitations = LaunchpadJobApplications.objects.select_related(
            'job', 'job__company', 'job__recruiter'
        ).filter(student_id=user_id)
        
        if status_filter:
            invitations = invitations.filter(status=status_filter)
        
      
        invitations = invitations.order_by('-invited_at')
    
        paginated_queryset = CommonUtils.get_paginated_queryset(
            invitations,
            request,
            ["job__title", "job__company__name", "status"],
            {
                "job_title": "job__title",
                "company_name": "job__company__name",
                "status": "status",
                "invited_at": "invited_at",
            },
        )
        
        data = []
        for invitation in paginated_queryset.get("queryset"):
            invitation_data = {
                'application_id': invitation.id,
                'job_id': invitation.job.id,
                'job_title': invitation.job.title,
                'company_name': invitation.job.company.name,
                'company_id': invitation.job.company.id,
                'recruiter_name': invitation.job.recruiter.name,
                'recruiter_email': invitation.job.recruiter.email,
                'recruiter_phone': invitation.job.recruiter.phone,
                'skills': invitation.job.skills,
                'experience': invitation.job.experience,
                'location': invitation.job.location,
                'salary_range': invitation.job.salary_range,
                'job_type': invitation.job.job_type,
                'domain': invitation.job.domain,
                'opening_type': invitation.job.opening_type,
                'minimum_karma': invitation.job.minimum_karma,
                'status': invitation.status,
                'invited_at': invitation.invited_at,
                'applied_at': invitation.applied_at,
            }
            
            if invitation.status == 'interview_scheduled':
                invitation_data['interview_details'] = {
                    'interview_date': getattr(invitation, 'interview_date', None),
                    'interview_time': getattr(invitation, 'interview_time', None),
                    'interview_platform': getattr(invitation, 'interview_platform', None),
                    'interview_link': getattr(invitation, 'interview_link', None),
                    'interview_scheduled_at': invitation.updated_at
                }
            
            if invitation.job.opening_type == "Task" and invitation.job.task:
                invitation_data['task_info'] = {
                    'task_id': invitation.job.task.id,
                    'task_description': invitation.job.task.task_description,
                    'task_verified': invitation.job.task.is_verified,
                    'task_hashtag': invitation.job.task.hashtags
                }

            if invitation.status in ['applied', 'interview_scheduled', 'accepted', 'rejected']:
                invitation_data['application_details'] = {
                    'resume_link': invitation.resume_link,
                    'linkedin_link': invitation.linkedin_link,
                    'portfolio_link': invitation.portfolio_link,
                    'cover_letter': invitation.cover_letter,
                    'other_link': invitation.other_link
                }
            
            data.append(invitation_data)
        
        return CustomResponse().paginated_response(
            data=data, 
            pagination=paginated_queryset.get("pagination")
        )

class StudentApplyToJobAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    def post(self, request):
        try:
            user_id = request.auth["id"]
            application_id = request.data.get('application_id')
            application = LaunchpadJobApplications.objects.select_related(
                'job', 'job__company', 'job__recruiter'
            ).get(id=application_id, student_id=user_id)
        except LaunchpadJobApplications.DoesNotExist:
            return CustomResponse(general_message="Job invitation not found.").get_failure_response()
        
        # Check if already applied
        if application.status != 'invited':
            return CustomResponse(
                general_message=f"Cannot apply to job. Current status: {application.status}"
            ).get_failure_response()
        
        # Validate required fields
        resume_link = request.data.get('resume_link')
        if not resume_link:
            return CustomResponse(
                message={'resume_link': ['Resume link is required.']},
                general_message="Application failed"
            ).get_failure_response()
        
        # Update application with form data
        application.resume_link = resume_link
        application.linkedin_link = request.data.get('linkedin_link', '')
        application.portfolio_link = request.data.get('portfolio_link', '')
        application.cover_letter = request.data.get('cover_letter', '')
        application.other_link = request.data.get('other_link', '')
        application.status = 'applied'
        application.applied_at = timezone.now()
        application.save()
        
        # Prepare response
        response_data = {
            'application_id': application.id,
            'job_info': {
                'id': application.job.id,
                'title': application.job.title,
                'company_name': application.job.company.name,
                'recruiter_name': application.job.recruiter.name,
                'opening_type': application.job.opening_type
            },
            'application_details': {
                'resume_link': application.resume_link,
                'linkedin_link': application.linkedin_link,
                'portfolio_link': application.portfolio_link,
                'cover_letter': application.cover_letter,
                'other_link': application.other_link
            },
            'status': application.status,
            'applied_at': application.applied_at
        }
        
        return CustomResponse(
            response=response_data,
            general_message="Application submitted successfully"
        ).get_success_response()

class AcceptedStudentsAPI(APIView):
    authentication_classes = [LaunchpadJWTPermission]
    
    def get(self, request, job_id=None):
        if request.auth["user_type"] != "recruiter":
            return CustomResponse(general_message="Only recruiters can view students.").get_failure_response()
        
        recruiter_id = request.auth["id"]
        status_filter = request.query_params.get('status', None)  # Get status filter from query params
        
        # Base query for applications
        applications = LaunchpadJobApplications.objects.select_related(
            'job', 'job__company', 'student', 'student__wallet_user'
        ).filter(
            job__recruiter_id=recruiter_id
        )
        
        # Apply status filter if provided
        if status_filter:
            if status_filter not in ['invited', 'applied', 'accepted', 'rejected', 'interview_scheduled']:
                return CustomResponse(
                    general_message="Invalid status. Valid statuses: invited, applied, accepted, rejected, interview_scheduled"
                ).get_failure_response()
            applications = applications.filter(status=status_filter)
        
        # Filter by specific job if provided
        if job_id:
            try:
                job = LaunchpadJobs.objects.get(id=job_id, recruiter_id=recruiter_id)
                applications = applications.filter(job_id=job_id)
            except LaunchpadJobs.DoesNotExist:
                return CustomResponse(general_message="Job not found or unauthorized.").get_failure_response()
        
        # Apply pagination
        paginated_queryset = CommonUtils.get_paginated_queryset(
            applications,
            request,
            ["student__full_name", "job__title", "job__company__name"],
            {
                "student_name": "student__full_name",
                "job_title": "job__title",
                "company_name": "job__company__name",
                "applied_at": "applied_at",
                "invited_at": "invited_at",
                "status": "status",
            },
        )
        
        data = []
        for application in paginated_queryset.get("queryset"):
            student = application.student
            job = application.job
            
            # Get student's college info
            college_link = student.user_organization_link_user.filter(
                org__org_type='College'
            ).first()
            
            # Get student's interest groups
            interest_groups = [
                {
                    'id': ig_link.ig.id,
                    'name': ig_link.ig.name
                }
                for ig_link in student.user_ig_link_user.all()
            ]
            
            application_data = {
                'application_id': application.id,
                'student_info': {
                    'id': student.id,
                    'full_name': student.full_name,
                    'email': student.email,
                    'muid': student.muid,
                    'profile_pic': student.profile_pic,
                    'karma': student.wallet_user.karma if student.wallet_user else 0,
                    'college_name': college_link.org.title if college_link else None,
                    'interest_groups': interest_groups
                },
                'job_info': {
                    'id': job.id,
                    'title': job.title,
                    'company_name': job.company.name,
                    'opening_type': job.opening_type,
                    'domain': job.domain,
                    'skills': job.skills,
                    'experience': job.experience,
                    'location': job.location,
                    'salary_range': job.salary_range
                },
                'application_details': {
                    'resume_link': application.resume_link,
                    'linkedin_link': application.linkedin_link,
                    'portfolio_link': application.portfolio_link,
                    'cover_letter': application.cover_letter,
                    'other_link': application.other_link
                } if application.status != 'invited' else None,  # Only show details if applied
                'status': application.status,
                'timeline': {
                    'invited_at': application.invited_at,
                    'applied_at': application.applied_at,
                    'interview_date': getattr(application, 'interview_date', None),
                    'interview_time': getattr(application, 'interview_time', None),
                    'decision_made_at': application.updated_at
                }
            }
            
            # Add task info if task-based job
            if job.opening_type == "Task" and job.task:
                application_data['task_info'] = {
                    'task_id': job.task.id,
                    'task_description': job.task.task_description,
                    'task_verified': job.task.is_verified,
                    'task_hashtag': job.task.hashtags
                }
            
            data.append(application_data)
        
        # Prepare summary statistics
        if job_id:
            # Stats for specific job
            job_stats = {
                'job_id': job_id,
                'job_title': job.title,
                'company_name': job.company.name,
                'total_invited': LaunchpadJobApplications.objects.filter(job_id=job_id, status='invited').count(),
                'total_applied': LaunchpadJobApplications.objects.filter(job_id=job_id, status='applied').count(),
                'total_accepted': LaunchpadJobApplications.objects.filter(job_id=job_id, status='accepted').count(),
                'total_rejected': LaunchpadJobApplications.objects.filter(job_id=job_id, status='rejected').count(),
                'filtered_count': len(data)
            }
        else:
            # Overall stats for recruiter
            job_stats = {
                'total_invited': LaunchpadJobApplications.objects.filter(job__recruiter_id=recruiter_id, status='invited').count(),
                'total_applied': LaunchpadJobApplications.objects.filter(job__recruiter_id=recruiter_id, status='applied').count(),
                'total_accepted': LaunchpadJobApplications.objects.filter(job__recruiter_id=recruiter_id, status='accepted').count(),
                'total_rejected': LaunchpadJobApplications.objects.filter(job__recruiter_id=recruiter_id, status='rejected').count(),
                'total_jobs': LaunchpadJobs.objects.filter(recruiter_id=recruiter_id).count(),
                'filtered_count': len(data)
            }
        
        return CustomResponse().paginated_response(
            data={
                'applications': data,
                'statistics': job_stats,
                'current_filter': status_filter or 'all'
            },
            pagination=paginated_queryset.get("pagination")
        )
class ScheduleInterviewAPI(APIView):
    authentication_classes = [LaunchpadJWTPermission]
    def post(self, request):
        user_id = request.auth["id"]
        application_id = request.data.get('application_id')
        interview_date = request.data.get('interview_date')
        interview_platform = request.data.get('interview_platform')
        interview_time = request.data.get('interview_time')
        interview_link = request.data.get('interview_link')
        if not application_id or not interview_date or not interview_time:
            return CustomResponse(
                message={
                    'application_id': ['Application ID is required.'],
                    'interview_date': ['Interview date is required.'],
                    'interview_time': ['Interview time is required.'],
                    'interview_platform': ['Interview platform is required.'],
                    'interview_link': ['Interview link is required.']
                },
                general_message="Scheduling failed"
            ).get_failure_response()
        
        try:
            application = LaunchpadJobApplications.objects.get(id=application_id)
            if application.status != 'applied':
                return CustomResponse(
                    general_message="Cannot schedule interview for this application."
                ).get_failure_response()
            
            # Update application with interview details
            application.interview_date = interview_date
            application.interview_time = interview_time
            application.interview_platform = interview_platform
            application.interview_link = interview_link
            application.updated_at = timezone.now()
            application.status = 'interview_scheduled'
            application.save()
            
            return CustomResponse(
                response={
                    'application_id': application.id,
                    'interview_date': application.interview_date,
                    'interview_platform': application.interview_platform,
                    'interview_time': application.interview_time,
                    'status': application.status
                },
                general_message="Interview scheduled successfully"
            ).get_success_response()
        
        except LaunchpadJobApplications.DoesNotExist:
            return CustomResponse(general_message="Application not found.").get_failure_response()
        

class ApplicationFinalDecisionAPI(APIView):
    authentication_classes = [LaunchpadJWTPermission]
    
    def post(self, request):
        user_type = request.auth["user_type"]
        if user_type not in ["recruiter", "company"]:
            return CustomResponse(general_message="Only recruiters and companies can make application final decisions.").get_failure_response()
        
        user_id = request.auth["id"]
        application_id = request.data.get('application_id')
        decision = request.data.get('decision')  # 'accepted' or 'rejected'
        
        if not application_id or not decision:
            return CustomResponse(
                message={
                    'application_id': ['Application ID is required.'],
                    'decision': ['Decision is required (accepted/rejected).']
                },
                general_message="Application final decision failed"
            ).get_failure_response()
        
        if decision not in ['accepted', 'rejected']:
            return CustomResponse(
                message={'decision': ['Decision must be either "accepted" or "rejected".']},
                general_message="Invalid decision"
            ).get_failure_response()
        
        try:
            application = LaunchpadJobApplications.objects.select_related(
                'job', 'job__company', 'job__recruiter', 'student', 'student__wallet_user'
            ).get(id=application_id)
            
            if user_type == "recruiter" and application.job.recruiter_id != user_id:
                return CustomResponse(
                    general_message="You can only make decisions on applications for your own jobs."
                ).get_failure_response()
            elif user_type == "company" and application.job.recruiter.company_id != user_id:
                return CustomResponse(
                    general_message="You can only make decisions on applications for jobs posted by your company."
                ).get_failure_response()
            
            valid_statuses = ['applied', 'interview_scheduled']
            if application.status not in valid_statuses:
                return CustomResponse(
                    general_message=f"Cannot make final decision on this application. Current status: {application.status}. Valid statuses: {', '.join(valid_statuses)}"
                ).get_failure_response()
            
            old_status = application.status
            application.status = decision
            application.updated_at = timezone.now()
            application.save()
            
            college_link = application.student.user_organization_link_user.filter(
                org__org_type='College'
            ).first()
            
            response_data = {
                'application_id': application.id,
                'decision': decision,
                'previous_status': old_status,
                'decision_made_at': application.updated_at,
                'decision_made_by': {
                    'user_type': user_type,
                    'user_id': user_id,
                    'name': application.job.recruiter.name if user_type == "recruiter" else application.job.company.name
                },
                'student_info': {
                    'id': application.student.id,
                    'full_name': application.student.full_name,
                    'email': application.student.email,
                    'muid': application.student.muid,
                    'karma': application.student.wallet_user.karma if application.student.wallet_user else 0,
                    'college_name': college_link.org.title if college_link else None
                },
                'job_info': {
                    'id': application.job.id,
                    'title': application.job.title,
                    'company_name': application.job.company.name,
                    'recruiter_name': application.job.recruiter.name,
                    'opening_type': application.job.opening_type,
                    'domain': application.job.domain
                },
                'application_timeline': {
                    'invited_at': application.invited_at,
                    'applied_at': application.applied_at,
                    'interview_date': getattr(application, 'interview_date', None),
                    'interview_time': getattr(application, 'interview_time', None),
                    'decision_made_at': application.updated_at
                }
            }
            
            success_message = f"Candidate {'accepted' if decision == 'accepted' else 'rejected'} successfully"
            
            return CustomResponse(
                response=response_data,
                general_message=success_message
            ).get_success_response()
            
        except LaunchpadJobApplications.DoesNotExist:
            return CustomResponse(
                general_message="Application not found."
            ).get_failure_response()
        except Exception as e:
            return CustomResponse(
                message={'detail': [str(e)]},
                general_message="Application final decision failed"
            ).get_failure_response()


class DeleteCompanyAPI(APIView):
    @role_required([RoleType.ADMIN.value])
    def patch(self, request):
        company_id = request.data.get("id")

        if not company_id:
            return CustomResponse(
                general_message="Company ID is required."
            ).get_failure_response()

        try:
            company = LaunchpadCompanies.objects.get(id=company_id)
        except LaunchpadCompanies.DoesNotExist:
            return CustomResponse(
                general_message="Company not found."
            ).get_failure_response()

        company.is_verified = False
        company.save()

        return CustomResponse(
            general_message="Company unverified successfully."
        ).get_success_response()


#<--------------------------------------------------- old launchpad ------------------------------------------------->
class Leaderboard(APIView):
    def get(self, request):
        total_karma_subquery = (
            KarmaActivityLog.objects.filter(
                user=OuterRef("id"),
                task__event="launchpad",
                appraiser_approved=True,
            )
            .values("user")
            .annotate(total_karma=Sum("karma"))
            .values("total_karma")
        )
        allowed_org_types = ["College", "School", "Company"]

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event="launchpad",
            appraiser_approved=True,
            task__hashtag="#lp24-introduction",
        ).values("user")

        latest_org_link = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__title")[:1]
        )

        latest_district = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__name")[:1]
        )

        latest_state = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__zone__state__name")[:1]
        )

        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                id__in=intro_task_completed_users,
            )
            .annotate(
                karma=Subquery(total_karma_subquery, output_field=IntegerField()),
                org=Subquery(latest_org_link),
                district_name=Subquery(latest_district),
                state=Subquery(latest_state),
                time_=Max("karma_activity_log_user__created_at"),
            )
            .order_by("-karma", "time_")
        )

        rank_list = list(users)
        for index, user in enumerate(rank_list):
            user.rank = index + 1

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users, request, ["full_name", "karma", "org", "district_name", "state"]
        )

        final_users = paginated_queryset.get("queryset")
        if request.query_params.get("search"):
            final_users = list(final_users)
            for user in final_users:
                user.rank = next(
                    rank_user.rank
                    for rank_user in rank_list
                    if rank_user.muid == user.muid
                )

        serializer = LaunchpadLeaderBoardSerializer(final_users, many=True)

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class TaskCompletedLeaderboard(APIView):
    def get(self, request):

        launchpad_tasks = TaskList.objects.filter(event="launchpad").values("id")

        completed_tasks_counts = (
            KarmaActivityLog.objects.filter(
                task__event="launchpad",
                appraiser_approved=True,
            )
            .values("user")
            .annotate(completed_tasks=Count("task", distinct=True))
            .filter(completed_tasks=launchpad_tasks.count())
        )

        allowed_org_types = ["College", "School", "Company"]

        completed_users = completed_tasks_counts.values("user")

        latest_org_link = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__title")[:1]
        )

        latest_district = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__name")[:1]
        )

        latest_state = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__zone__state__name")[:1]
        )

        wallet_subquery = Wallet.objects.filter(user=OuterRef("id")).values("karma")[:1]

        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                id__in=completed_users,
            )
            .annotate(
                karma=Subquery(wallet_subquery, output_field=IntegerField()),
                org=Subquery(latest_org_link),
                district_name=Subquery(latest_district),
                state=Subquery(latest_state),
                time_=Max("karma_activity_log_user__created_at"),
            )
            .order_by("-karma", "time_")
        )

        rank_list = list(users)
        for index, user in enumerate(rank_list):
            user.rank = index + 1

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users, request, ["muid", "full_name", "org"]
        )

        final_users = paginated_queryset.get("queryset")
        if request.query_params.get("search"):
            final_users = list(final_users)
            for user in final_users:
                user.rank = next(
                    rank_user.rank
                    for rank_user in rank_list
                    if rank_user.muid == user.muid
                )

        serializer = TaskCompletedLeaderBoardSerializer(final_users, many=True)
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class ListParticipantsAPI(APIView):
    def get(self, request):
        allowed_org_types = ["College", "School", "Company"]
        allowed_levels = LaunchPadLevels.get_all_values()

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event="launchpad",
            appraiser_approved=True,
            task__hashtag="#lp24-introduction",
        ).values("user")

        latest_org_link = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__title")[:1]
        )

        latest_district = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__name")[:1]
        )

        latest_state = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__zone__state__name")[:1]
        )

        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                id__in=intro_task_completed_users,
            )
            .prefetch_related(
                Prefetch(
                    "user_role_link_user",
                    queryset=UserRoleLink.objects.filter(
                        verified=True, role__title__in=allowed_levels
                    ).select_related("role"),
                )
            )
            .annotate(
                org=Subquery(latest_org_link),
                district_name=Subquery(latest_district),
                state=Subquery(latest_state),
                level=F("user_role_link_user__role__title"),
                time_=Max("karma_activity_log_user__created_at"),
            )
            .filter(Q(level__in=allowed_levels) | Q(level__isnull=True))
            .distinct()
        )

        if district := request.query_params.get("district"):
            users = users.filter(district_name=district)
        if org := request.query_params.get("org"):
            users = users.filter(org=org)
        if level := request.query_params.get("level"):
            users = users.filter(level=level)
        if state := request.query_params.get("state"):
            users = users.filter(state=state)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["full_name", "level", "org", "district_name", "state"],
            sort_fields={
                "full_name": "full_name",
                "org": "org",
                "district_name": "district_name",
                "state": "state",
                "level": "level",
            },
        )

        serializer = LaunchpadParticipantsSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class LaunchpadDetailsCount(APIView):
    def get(self, request):
        allowed_org_types = ["College", "School", "Company"]
        allowed_levels = LaunchPadLevels.get_all_values()

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event="launchpad",
            appraiser_approved=True,
            task__hashtag="#lp24-introduction",
        ).values("user")

        latest_org_link = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__title")[:1]
        )

        latest_district = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__name")[:1]
        )

        latest_state = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__zone__state__name")[:1]
        )

        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                id__in=intro_task_completed_users,
            )
            .prefetch_related(
                Prefetch(
                    "user_role_link_user",
                    queryset=UserRoleLink.objects.filter(
                        verified=True, role__title__in=allowed_levels
                    ).select_related("role"),
                )
            )
            .annotate(
                org=Subquery(latest_org_link),
                district_name=Subquery(latest_district),
                state=Subquery(latest_state),
                level=F("user_role_link_user__role__title"),
                time_=Max("karma_activity_log_user__created_at"),
            )
            .distinct()
        )

        # Count participants at each level
        level_counts = {
            "total_participants": users.values("id").count(),
            "Level_1": users.filter(level=LaunchPadLevels.LEVEL_1.value).count(),
            "Level_2": users.filter(level=LaunchPadLevels.LEVEL_2.value).count(),
            "Level_3": users.filter(level=LaunchPadLevels.LEVEL_3.value).count(),
            "Level_4": users.filter(level=LaunchPadLevels.LEVEL_4.value).count(),
        }

        return CustomResponse(response=level_counts).get_success_response()


class CollegeData(APIView):
    def get(self, request):
        allowed_levels = LaunchPadLevels.get_all_values()

        org = (
            Organization.objects.filter(
                org_type="College",
            )
            .prefetch_related(
                Prefetch(
                    "user_organization_link_org",
                    queryset=UserOrganizationLink.objects.filter(
                        user__user_role_link_user__role__title__in=allowed_levels
                    ),
                )
            )
            .filter(
                user_organization_link_org__user__user_role_link_user__role__title__in=allowed_levels
            )
            .annotate(
                district_name=F("district__name"),
                state=F("district__zone__state__name"),
                total_users=Count("user_organization_link_org__user"),
                level1=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_1.value
                    ),
                ),
                level2=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_2.value
                    ),
                ),
                level3=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_3.value
                    ),
                ),
                level4=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_4.value
                    ),
                ),
            )
            .order_by("-total_users")
        )

        if district := request.query_params.get("district"):
            org = org.filter(district_name=district)
        if title := request.query_params.get("title"):
            org = org.filter(title=title)
        if state := request.query_params.get("state"):
            org = org.filter(state=state)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            org,
            request,
            ["title", "district_name", "state"],
            sort_fields={
                "title": "title",
                "district_name": "district_name",
                "state": "state",
            },
        )

        serializer = CollegeDataSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class LaunchPadUser(APIView):

    def post(self, request):
        data = request.data
        auth_mail = data.pop("current_user", None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (
            auth_user := LaunchPadUsers.objects.filter(
                email=auth_mail, role=LaunchPadRoles.ADMIN.value
            ).first()
        ):
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        serializer = LaunchpadUserSerializer(data=data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        colleges = data.get("colleges")
        errors = {}
        error = False
        not_found_colleges = []
        user = serializer.save()
        for college in colleges:
            if not Organization.objects.filter(id=college, org_type="College").exists():
                error = True
                not_found_colleges.append(college)
            elif link := LaunchPadUserCollegeLink.objects.filter(
                college_id=college
            ).first():
                link.delete()
            else:
                LaunchPadUserCollegeLink.objects.create(
                    id=uuid.uuid4(),
                    user=user,
                    college_id=college,
                    created_by=auth_user,
                    updated_by=auth_user,
                )
        errors[data.get("email")] = {}
        errors[data.get("email")]["not_found_colleges"] = not_found_colleges
        if error:
            return CustomResponse(message=errors).get_failure_response()
        return CustomResponse(
            general_message="Successfully added user"
        ).get_success_response()

    def get(self, request):
        auth_mail = request.query_params.get("current_user", None)
        if not LaunchPadUsers.objects.filter(
            email=auth_mail, role=LaunchPadRoles.ADMIN.value
        ).exists():
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        users = LaunchPadUsers.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            users,
            request,
            ["full_name", "phone_number", "email", "role", "district", "zone"],
        )

        serializer = LaunchpadUserListSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

    def put(self, request, email):
        data = request.data
        auth_mail = data.pop("current_user", None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (
            auth_user := LaunchPadUsers.objects.filter(
                email=auth_mail, role=LaunchPadRoles.ADMIN.value
            ).first()
        ):
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        try:
            user = LaunchPadUsers.objects.get(email=email)
        except LaunchPadUsers.DoesNotExist:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()
        serializer = LaunchpadUpdateUserSerializer(
            user, data=data, context={"auth_user": auth_user}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Successfully updated user"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class LaunchPadUserPublic(APIView):

    def get(self, request, email):
        try:
            user = LaunchPadUsers.objects.get(email=email)
        except LaunchPadUsers.DoesNotExist:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()
        serializer = LaunchpadUserListSerializer(user)
        return CustomResponse(response=serializer.data).get_success_response()


class UserProfile(APIView):

    def get(self, request):
        auth_mail = request.query_params.get("current_user", None)
        if not LaunchPadUsers.objects.filter(email=auth_mail).exists():
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        user = LaunchPadUsers.objects.get(email=auth_mail)
        serializer = LaunchpadUserListSerializer(user)
        return CustomResponse(response=serializer.data).get_success_response()

    def put(self, request):
        data = request.data
        auth_mail = data.pop("current_user", None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (user := LaunchPadUsers.objects.filter(email=auth_mail).first()):
            return CustomResponse(general_message="Unauthorized").get_failure_response()

        serializer = UserProfileUpdateSerializer(user, data=data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Successfully updated user"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class UserBasedCollegeData(APIView):

    def get(self, request):
        auth_mail = request.query_params.get("current_user", None)
        if not LaunchPadUsers.objects.filter(email=auth_mail).exists():
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        user = LaunchPadUsers.objects.get(email=auth_mail)
        colleges = LaunchPadUserCollegeLink.objects.filter(user=user)
        college_ids = [college.college_id for college in colleges]

        allowed_levels = LaunchPadLevels.get_all_values()

        org = (
            Organization.objects.filter(org_type="College", id__in=college_ids)
            .prefetch_related(
                Prefetch(
                    "user_organization_link_org",
                    queryset=UserOrganizationLink.objects.filter(
                        user__user_role_link_user__role__title__in=allowed_levels
                    ),
                )
            )
            .filter(
                user_organization_link_org__user__user_role_link_user__role__title__in=allowed_levels
            )
            .annotate(
                district_name=F("district__name"),
                state=F("district__zone__state__name"),
                total_users=Count("user_organization_link_org__user"),
                level1=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_1.value
                    ),
                ),
                level2=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_2.value
                    ),
                ),
                level3=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_3.value
                    ),
                ),
                level4=Count(
                    "user_organization_link_org__user",
                    filter=Q(
                        user_organization_link_org__user__user_role_link_user__role__title=LaunchPadLevels.LEVEL_4.value
                    ),
                ),
            )
            .order_by("-total_users")
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            org, request, ["title", "district_name", "state"]
        )

        serializer = CollegeDataSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class BulkLaunchpadUser(APIView):

    def post(self, request):
        data = request.data
        auth_mail = data.pop("current_user", None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (
            auth_user := LaunchPadUsers.objects.filter(
                email=auth_mail, role=LaunchPadRoles.ADMIN.value
            ).first()
        ):
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        try:
            file_obj = request.FILES["user_data"]
        except KeyError:
            return CustomResponse(
                general_message={"File not found."}
            ).get_failure_response()
        excel_data = ImportCSV()
        excel_data = excel_data.read_excel_file(file_obj)
        if not excel_data:
            return CustomResponse(
                general_message={"Empty csv file."}
            ).get_failure_response()
        errors = {}
        error = False

        for data in excel_data[1:]:
            not_found_colleges = []
            data["colleges"] = (
                data["colleges"].split(",") if data.get("colleges") else []
            )
            serializer = LaunchpadUserSerializer(data=data)
            if not serializer.is_valid():
                continue
            user = serializer.save()
            if data.get("colleges") is None:
                continue
            for college in data.get("colleges"):
                if not (
                    org := Organization.objects.filter(
                        title=college, org_type="College"
                    ).first()
                ):
                    error = True
                    not_found_colleges.append(college)
                elif link := LaunchPadUserCollegeLink.objects.filter(
                    college_id=college
                ).first():
                    link.delete()
                else:
                    LaunchPadUserCollegeLink.objects.create(
                        id=uuid.uuid4(),
                        user=user,
                        college=org,
                        created_by=auth_user,
                        updated_by=auth_user,
                    )
            errors[data.get("email")] = {}
            errors[data.get("email")]["not_found_colleges"] = not_found_colleges
        if error:
            return CustomResponse(message=errors).get_failure_response()
        return CustomResponse(
            general_message="Successfully added users"
        ).get_success_response()


class LaunchPadListAdmin(APIView):

    def get(self, request):
        auth_mail = request.query_params.get("current_user", None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if not (
            auth_user := LaunchPadUsers.objects.filter(
                email=auth_mail, role=LaunchPadRoles.ADMIN.value
            ).first()
        ):
            return CustomResponse(general_message="Unauthorized").get_failure_response()
        total_karma_subquery = (
            KarmaActivityLog.objects.filter(
                user=OuterRef("id"),
                task__event="launchpad",
                appraiser_approved=True,
            )
            .values("user")
            .annotate(total_karma=Sum("karma"))
            .values("total_karma")
        )
        allowed_org_types = ["College", "School", "Company"]

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event="launchpad",
            appraiser_approved=True,
            task__hashtag="#lp24-introduction",
        ).values("user")

        latest_org_link = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__title")[:1]
        )

        latest_district = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__name")[:1]
        )

        latest_state = (
            UserOrganizationLink.objects.filter(
                user=OuterRef("id"), org__org_type__in=allowed_org_types
            )
            .order_by("-created_at")
            .values("org__district__zone__state__name")[:1]
        )

        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                id__in=intro_task_completed_users,
            )
            .annotate(
                karma=Subquery(total_karma_subquery, output_field=IntegerField()),
                org=Subquery(latest_org_link),
                district_name=Subquery(latest_district),
                state=Subquery(latest_state),
                time_=Max("karma_activity_log_user__created_at"),
            )
            .order_by("-karma", "time_")
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            users, request, ["full_name", "karma", "org", "district_name", "state"]
        )

        serializer = LaunchpadLeaderBoardSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


class BaseAPI(APIView):
    def get_authenticated_user(self, request, launchpad_id):
        auth_mail = request.query_params.get("current_user", None)
        auth_mail = auth_mail[0] if isinstance(auth_mail, list) else auth_mail
        if launchpad_id is None:
            return (
                None,
                CustomResponse(
                    general_message="No launchpad id provided"
                ).get_failure_response(),
            )
        if not (
            auth_user := LaunchPadUsers.objects.filter(
                email=auth_mail, role=LaunchPadRoles.ADMIN.value
            ).first()
        ):
            return (
                None,
                CustomResponse(general_message="Unauthorized").get_failure_response(),
            )
        try:
            user = LaunchPad.objects.get(launchpad_id=launchpad_id).user
        except LaunchPad.DoesNotExist:
            return (
                None,
                CustomResponse(
                   
                    general_message="Invalid Launchpad ID"
                ).get_failure_response(),
            )
        return user, None


class UserProfileAPI(BaseAPI):
    def get(self, request, launchpad_id=None):
        user, response = self.get_authenticated_user(request, launchpad_id)
        if response:
            return response
        serializer = UserProfileSerializer(user, many=False)
        launchpad_karma = (
            KarmaActivityLog.objects.filter(
                user=user,
                task__event="launchpad",
                appraiser_approved=True,
            ).aggregate(total_karma=Sum("karma"))["total_karma"]
            or 0
        )
        rank_serializer = LaunchPadRankSerializer(user)
        launchpad_rank = rank_serializer.data["launchpad_rank"]

        data = serializer.data
        data["launchpad_karma"] = launchpad_karma
        data["launchpad_rank"] = launchpad_rank
        return CustomResponse(response=data).get_success_response()


class GetSocialsAPI(BaseAPI):
    def get(self, request, launchpad_id=None):
        user, response = self.get_authenticated_user(request, launchpad_id)
        if response:
            return response
        social_instance = Socials.objects.filter(user_id=user.id).first()
        serializer = LinkSocials(instance=social_instance)
        return CustomResponse(response=serializer.data).get_success_response()


class UserLevelsAPI(BaseAPI):
    def get(self, request, launchpad_id=None):
        user, response = self.get_authenticated_user(request, launchpad_id)
        if response:
            return response
        user_levels_link_query = Level.objects.all().order_by("level_order")
        serializer = UserLevelSerializer(
            user_levels_link_query, many=True, context={"user_id": user.id}
        )
        return CustomResponse(response=serializer.data).get_success_response()


class UserLogAPI(BaseAPI):
    def get(self, request, launchpad_id=None):
        launchpad_log = request.query_params.get("launchpad_log", False)
        user, response = self.get_authenticated_user(request, launchpad_id)
        if response:
            return response

        query = Q(user=user.id, appraiser_approved=True)
        if launchpad_log:
            query &= Q(task__event="launchpad")
        karma_activity_log = KarmaActivityLog.objects.filter(query).order_by(
            "-created_at"
        )
        if not karma_activity_log.exists():
            return CustomResponse(
                general_message="No karma details available for user"
            ).get_success_response()

        serializer = UserLogSerializer(karma_activity_log, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class IGLeaderboardView(APIView):
    def get(self, request):
        category = request.query_params.get("category")
        # ig_id = request.query_params.get("ig_id")

        if category is None:
            return CustomResponse(
                general_message="No category provided"
            ).get_failure_response()

        # if ig_id is None:
        #     return CustomResponse(
        #         general_message="No IG ID provided"
        #     ).get_failure_response()

        logs = (
            KarmaActivityLog.objects.select_related("user", "task", "task__ig")
            .prefetch_related("user__wallet_user")
            .filter(task__ig__category=category, appraiser_approved=True)
            .values("user_id", "task__ig__category")
            .annotate(
                category_karma=Sum("karma"),
            )
            .order_by("-category_karma")
            .values(
                "user_id",
                "user__full_name",
                "user__email",
                "user__muid",
                # "user__profile_pic",
                "category_karma",
                "user__wallet_user__karma",
            )
        )
        fs = FileSystemStorage()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            logs,
            request,
            search_fields=[
                "user__full_name",
                "user__email",
                "user__muid",
            ],
            sort_fields={
                "category_karma": "category_karma",
                "total_karma": "user__wallet_user__karma",
            },
        )

        ig_data = {}
        for entry in (
            KarmaActivityLog.objects.select_related("task__ig")
            .filter(
                appraiser_approved=True,
                task__ig__category=category,
                user_id__in=[
                    row.get("user_id") for row in paginated_queryset.get("queryset")
                ],
            )
            .values("task__ig_id", "user_id")
            .annotate(ig_karma=Sum("karma"))
            .values("user_id", "ig_karma", "task__ig__name", "task__ig_id")
        ):
            if not ig_data.get(entry.get("user_id")):
                ig_data[entry.get("user_id")] = []
            ig_data[entry.get("user_id")].append(
                {
                    "ig_id": entry.get("task__ig_id"),
                    "ig_karma": entry.get("ig_karma"),
                    "ig_name": entry.get("task__ig__name"),
                }
            )

        data = [
            {
                "full_name": row.get("user__full_name"),
                "email": row.get("user__email"),
                "muid": row.get("user__muid"),
                "profile_pic": (
                    f"{decouple_config('BE_DOMAIN_NAME')}{fs.url('user/profile/{}.png'.format('user_id'))}"
                    if fs.exists("user/profile/{}.png".format("user_id"))
                    else None
                ),
                "category_karma": row.get("category_karma"),
                "total_karma": row.get("user__wallet_user__karma"),
                "ig_data": ig_data.get(row.get("user_id")),
            }
            for row in paginated_queryset.get("queryset")
        ]
        return CustomResponse().paginated_response(
            data=data, pagination=paginated_queryset.get("pagination")
        )

class ForgotPasswordAPI(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors,
                general_message="Invalid request"
            ).get_failure_response()

        email = serializer.validated_data['email']
        user_type = serializer.validated_data['user_type']
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=1)  # Token expires in 1 hour
        
        try:
            if user_type == 'company':
                user = LaunchpadCompanies.objects.get(poc_email=email)
                user.reset_token = reset_token
                user.reset_token_expires = expires_at
                user.save()
                
                user_name = user.name or user.poc_name
                user_email = user.poc_email
                
            else:  # recruiter
                user = LaunchpadRecruiters.objects.get(email=email)
                user.reset_token = reset_token
                user.reset_token_expires = expires_at
                user.save()
                
                user_name = user.name
                user_email = user.email
            
            # Send reset email
            try:
                reset_link = f"{decouple.config('LAUNCHPAD_FR_DOMAIN_NAME')}/reset-password?token={reset_token}&type={user_type}"
                send_template_mail(
                    context={
                        "email": user_email,
                        "full_name": user_name,
                        "reset_link": reset_link,
                        "expires_in": "1 hour"
                    },
                    subject="Password Reset - MuLearn Launchpad",
                    address=["launchpad-password-reset.html"]
                )
            except Exception as e:
                return CustomResponse(
                    general_message="Failed to send reset email. Please try again."
                ).get_failure_response()
            
            return CustomResponse(
                general_message="Password reset link has been sent to your email."
            ).get_success_response()
            
        except (LaunchpadCompanies.DoesNotExist, LaunchpadRecruiters.DoesNotExist):
            # Don't reveal if user exists or not for security
            return CustomResponse(
                general_message="If an account with this email exists, a password reset link has been sent."
            ).get_success_response()

class ResetPasswordAPI(APIView):
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors,
                general_message="Invalid request"
            ).get_failure_response()

        user = serializer.validated_data['user']
        new_password = serializer.validated_data['new_password']
        
        # Reset password
        user.password = make_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        user.save()
        
        return CustomResponse(
            general_message="Password has been reset successfully. You can now login with your new password."
        ).get_success_response()

class VerifyResetTokenAPI(APIView):
    def post(self, request):
        token = request.data.get('token')
        user_type = request.data.get('user_type')
        
        if not token or not user_type:
            return CustomResponse(
                general_message="Token and user type are required."
            ).get_failure_response()
        
        now = timezone.now()
        
        try:
            if user_type == 'company':
                user = LaunchpadCompanies.objects.get(
                    reset_token=token,
                    reset_token_expires__gt=now
                )
                user_name = user.name or user.poc_name
            else:
                user = LaunchpadRecruiters.objects.get(
                    reset_token=token,
                    reset_token_expires__gt=now
                )
                user_name = user.name
            
            return CustomResponse(
                response={
                    'valid': True,
                    'user_name': user_name,
                    'expires_at': user.reset_token_expires
                },
                general_message="Token is valid"
            ).get_success_response()
            
        except (LaunchpadCompanies.DoesNotExist, LaunchpadRecruiters.DoesNotExist):
            return CustomResponse(
                response={'valid': False},
                general_message="Invalid or expired token"
            ).get_failure_response()

class ChangePasswordAPI(APIView):
    authentication_classes = [LaunchpadJWTPermission]
    
    def post(self, request):
        user_type = request.auth["user_type"]
        user_id = request.auth["id"]
        
        serializer = ChangePasswordSerializer(data=request.data)
        
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors,
                general_message="Invalid request"
            ).get_failure_response()

        current_password = serializer.validated_data['current_password']
        new_password = serializer.validated_data['new_password']
        
        try:
            if user_type == 'company':
                user = LaunchpadCompanies.objects.get(id=user_id)
            else:
                user = LaunchpadRecruiters.objects.get(id=user_id)
            
            # Verify current password
            if not check_password(current_password, user.password):
                return CustomResponse(
                    message={'current_password': ['Current password is incorrect.']},
                    general_message="Password change failed"
                ).get_failure_response()
            
            # Update password
            user.password = make_password(new_password)
            user.save()
            
            return CustomResponse(
                general_message="Password changed successfully."
            ).get_success_response()
            
        except (LaunchpadCompanies.DoesNotExist, LaunchpadRecruiters.DoesNotExist):
            return CustomResponse(
                general_message="User not found."
            ).get_failure_response()

