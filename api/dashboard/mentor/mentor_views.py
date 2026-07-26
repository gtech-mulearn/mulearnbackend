import re
from rest_framework.views import APIView
from django.db.models import Q, Case, When
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.utils import CommonUtils, DateTimeUtils
from db.user import UserMentor, Socials, MentorApplication
from db.mentor import MentorshipSession
from db.organization import Organization
from db.task import KarmaActivityLog
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, inline_serializer
from rest_framework import serializers as rest_serializers
from . import serializers
from .dash_mentor_helper import get_mentor_overview


class MentorRegistrationAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Submit a new mentor registration.",
        request=serializers.MentorRegisterSerializer,
        responses={200: serializers.MentorRegisterSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        mentor_tier = request.data.get('mentor_tier')
        org_id = request.data.get('org')

        # Prevent duplicate PENDING or APPROVED applications.
        if mentor_tier == MentorApplication.MentorTier.IG_MENTOR.value:
            # A user can only have one active/pending IG_MENTOR application, regardless of org.
            if MentorApplication.objects.filter(user_id=user_id, mentor_tier=mentor_tier, status__in=[MentorApplication.Status.PENDING, MentorApplication.Status.APPROVED]).exists():
                return CustomResponse(
                    general_message="You already have an active or pending IG mentor application."
                ).get_failure_response()
        elif mentor_tier in [MentorApplication.MentorTier.COMPANY_MENTOR.value, MentorApplication.MentorTier.CAMPUS_MENTOR.value]:
            # For Company/Campus mentors, the org is part of the unique scope.
            if not org_id:
                # This will be caught by the serializer, but good to have a check here too.
                return CustomResponse(general_message="Organization is required for this mentor tier.").get_failure_response()

            if MentorApplication.objects.filter(user_id=user_id, mentor_tier=mentor_tier, org_id=org_id, status__in=[MentorApplication.Status.PENDING, MentorApplication.Status.APPROVED]).exists():
                tier_name = str(mentor_tier).replace('_', ' ').lower()
                return CustomResponse(
                    general_message=f"You already have an active or pending {tier_name} application for this organization."
                ).get_failure_response()

        serializer = serializers.MentorRegisterSerializer(
            data=request.data, context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()

            response_data = serializer.data
            return CustomResponse(
                general_message="Mentor registration submitted successfully.",
                response=response_data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Update a pending mentor application or resubmit a rejected one.",
        request=serializers.MentorUpdateSerializer,
        responses={200: serializers.MentorUpdateSerializer},
    )
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        mentor_id = request.data.get('id')
        if not mentor_id:
            return CustomResponse(
                general_message="Mentor application ID ('id') is required for an update."
            ).get_failure_response()

        application = MentorApplication.objects.filter(id=mentor_id, user_id=user_id).first()

        if not application:
            return CustomResponse(
                general_message="No mentor registration request found for your account with the given ID."
            ).get_failure_response(status_code=404)

        if application.status == MentorApplication.Status.APPROVED:
            return CustomResponse(
                general_message="Your mentor application is already approved. Please use the profile endpoint to update your details."
            ).get_failure_response()

        serializer = serializers.MentorUpdateSerializer(
            application, data=request.data, partial=True, context={"user_id": user_id}
        )

        if serializer.is_valid():
            if 'linkedin' in serializer.validated_data:
                linkedin_url = serializer.validated_data.get('linkedin')
                socials, created = Socials.objects.get_or_create(user_id=user_id)
                socials.linkedin = linkedin_url or None
                socials.save(update_fields=['linkedin'])

            if application.status == MentorApplication.Status.REJECTED:
                serializer.save(status=MentorApplication.Status.PENDING, verification_note=None)
                msg = "Mentor registration updated and resubmitted successfully."
            else:
                serializer.save()
                msg = "Mentor application updated successfully."

            response_data = serializer.data
            socials = Socials.objects.filter(user_id=user_id).first()
            response_data['linkedin'] = socials.linkedin if socials else None

            return CustomResponse(
                general_message=msg,
                response=response_data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class MentorStatusAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Check the status of a mentor registration.",
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        applications = MentorApplication.objects.filter(user_id=user_id).order_by('-created_at')
        if not applications.exists():
            return CustomResponse(
                general_message="No mentor requests found for your account."
            ).get_failure_response(status_code=404)

        from .dash_mentor_helper import get_mentor_company

        response_list = []
        for app in applications:
            organization = get_mentor_company(app)

            response_item = {
                "id": app.id,
                "status": app.status,
                "mentor_tier": app.mentor_tier,
                "organization": organization,
                "verified_by": getattr(app.verified_by, "full_name", None) if app.verified_by else None,
                "verified_at": app.verified_at,
                "created_at": app.created_at,
            }

            if app.status == MentorApplication.Status.REJECTED:
                response_item["rejection_reason"] = app.verification_note

            response_list.append(response_item)

        return CustomResponse(
            general_message="Successfully retrieved all mentor application statuses.",
            response=response_list
        ).get_success_response()

class MentorActivityListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Get recent activity of the currently logged-in mentor (sessions created, tasks appraised).",
        responses={200: serializers.MentorActivitySerializer(many=True)},
    )
    @role_required([RoleType.MENTOR.value, RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        # 1. Fetch MentorshipSessions created by this mentor
        sessions = MentorshipSession.objects.filter(
            created_by_id=user_id,
            is_deleted=False
        )

        # 2. Fetch KarmaActivityLogs appraised by this mentor
        appraisals = KarmaActivityLog.objects.filter(
            appraiser_approved_by_id=user_id
        ).select_related("task")

        activities = []
        for session in sessions:
            activities.append({
                "id": session.id,
                "activity_type": "SESSION_CREATED",
                "title": session.title,
                "description": session.description,
                "date": session.created_at,
                "status": session.status,
            })

        for log in appraisals:
            status_text = "Pending"
            if log.appraiser_approved:
                status_text = "Approved"
            elif log.appraiser_approved is False:
                status_text = "Rejected"
                
            activities.append({
                "id": str(log.id),
                "activity_type": "TASK_APPRAISED",
                "title": log.task.title if log.task else "Unknown Task",
                "description": None,
                "date": log.updated_at,
                "status": status_text,
            })

        # Sort activities by date descending
        activities.sort(key=lambda x: x["date"] or x.get("created_at") or "", reverse=True)

        # Paginate the combined list
        paginated_queryset = CommonUtils.get_paginated_queryset(
            activities, request,
            search_fields=["title", "activity_type", "status"],
            sort_fields={"date": "date"}
        )

        serializer = serializers.MentorActivitySerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

class MentorProfileAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Retrieve the profile of a verified mentor.",
        responses={200: serializers.MentorDetailSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        mentor_profile = UserMentor.objects.filter(user_id=user_id).first()

        if not mentor_profile:
            return CustomResponse(
                general_message="No approved mentor profiles found."
            ).get_failure_response(status_code=404)

        serializer = serializers.MentorDetailSerializer(mentor_profile)
        response_data = serializer.data

        socials = Socials.objects.filter(user_id=user_id).first()
        linkedin_url = socials.linkedin if socials else None
        response_data['linkedin'] = linkedin_url

        return CustomResponse(
            general_message="Successfully retrieved mentor profile.",
            response=response_data
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Update the profile of a verified mentor.",
        request=serializers.MentorProfileUpdateSerializer,
        responses={200: serializers.MentorDetailSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        profile = UserMentor.objects.filter(user_id=user_id).first()

        if not profile:
            return CustomResponse(
                general_message="Mentor profile not found."
            ).get_failure_response(status_code=404)

        serializer = serializers.MentorProfileUpdateSerializer(
            profile, data=request.data, partial=True, context={"user_id": user_id}
        )
        
        if serializer.is_valid():
            if 'linkedin' in serializer.validated_data:
                linkedin_url = serializer.validated_data.get('linkedin')
                socials, _ = Socials.objects.get_or_create(
                    user_id=user_id,
                    defaults={
                        'created_by_id': user_id,
                        'updated_by_id': user_id,
                        'created_at': DateTimeUtils.get_current_utc_time(),
                        'updated_at': DateTimeUtils.get_current_utc_time()
                    }
                )
                socials.linkedin = linkedin_url or None
                socials.updated_by_id = user_id
                socials.updated_at = DateTimeUtils.get_current_utc_time()
                socials.save()
 
            serializer.save()
 
            response_serializer = serializers.MentorDetailSerializer(profile)
            response_data = response_serializer.data
            socials = Socials.objects.filter(user_id=user_id).first()
            response_data['linkedin'] = socials.linkedin if socials else None

            return CustomResponse(
                general_message="Mentor profile updated successfully.",
                response=response_data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class MentorListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="List all mentor applications with filtering.",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("mentor_tier", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: serializers.MentorListSerializer(many=True)},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        # Find users who are already approved mentors to identify change requests
        approved_mentor_user_ids = MentorApplication.objects.filter(
            status=MentorApplication.Status.APPROVED
        ).values_list('user_id', flat=True).distinct()

        # Exclude pending applications from these users (which are change requests)
        mentors = MentorApplication.objects.select_related('user').exclude(
            user_id__in=approved_mentor_user_ids,
            status=MentorApplication.Status.PENDING
        )

        status = request.query_params.get("status")
        mentor_tier = request.query_params.get("mentor_tier")

        if status:
            mentors = mentors.filter(status=status)
        if mentor_tier:
            mentors = mentors.filter(mentor_tier=mentor_tier)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            mentors, request, 
            search_fields=["user__full_name", "user__email"],
            sort_fields={"created_at": "created_at", "status": "status", "user_full_name": "user__full_name"}
        )
        
        serializer = serializers.MentorListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

class MentorDetailAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Get details of a specific mentor by ID.",
        responses={200: serializers.MentorDetailSerializer},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request, mentor_id):
        application = MentorApplication.objects.filter(id=mentor_id).first()
        if not application:
            return CustomResponse(
                general_message="Mentor application not found."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.MentorListSerializer(application)
        return CustomResponse(response=serializer.data).get_success_response()

class MentorChangeRequestListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="List all mentor company change applications for admin review.",
        responses={200: serializers.MentorListSerializer(many=True)},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        # Find users who are already approved mentors
        approved_mentor_user_ids = MentorApplication.objects.filter(
            status=MentorApplication.Status.APPROVED
        ).values_list('user_id', flat=True).distinct()

        # Get pending applications from these users
        change_requests = MentorApplication.objects.select_related('user').filter(
            user_id__in=approved_mentor_user_ids,
            status=MentorApplication.Status.PENDING
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            change_requests, request, 
            search_fields=["user__full_name", "user__email"],
            sort_fields={"created_at": "created_at", "user_full_name": "user__full_name"}
        )
        
        serializer = serializers.MentorListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={"data": serializer.data, "pagination": paginated_queryset.get("pagination")}
        ).get_success_response()

def _is_company_owner_of(actor_id, mentor):
    """
    True if `actor_id` owns the verified Company that `mentor`'s
    COMPANY_MENTOR application is scoped to. Verification authority for a
    company's own mentor applications belongs to that company's owner, not
    only platform admins.
    """
    if mentor.mentor_tier != MentorApplication.MentorTier.COMPANY_MENTOR or not mentor.org:
        return False

    from db.company import Company
    return Company.objects.filter(
        company_user_id=actor_id,
        status="verified",
        name=mentor.org.title,
    ).exists()


class MentorVerifyAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description=(
            "Verify or reject a mentor application. Platform admins can "
            "verify any application; a Company's owner can verify "
            "COMPANY_MENTOR applications scoped to their own company."
        ),
        request=serializers.MentorVerifySerializer,
    )
    def patch(self, request, mentor_id):
        user_id = JWTUtils.fetch_user_id(request)
        application = MentorApplication.objects.select_related('verified_by', 'updated_by', 'org').filter(id=mentor_id).first()

        if not application:
            return CustomResponse(
                general_message="Mentor request not found."
            ).get_failure_response(status_code=404)

        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles
        is_owner = _is_company_owner_of(user_id, application)

        # Authorization check
        can_verify = False
        if application.mentor_tier == MentorApplication.MentorTier.COMPANY_MENTOR:
            # For company mentors, ONLY the company owner can verify
            if is_owner:
                can_verify = True
        else:
            # For other tiers (like IG_MENTOR), only admin can verify
            if is_admin:
                can_verify = True
        
        if not can_verify:
            return CustomResponse(
                general_message="You are not authorized to verify this mentor application."
            ).get_failure_response(status_code=403)

        if application.status in [MentorApplication.Status.APPROVED, MentorApplication.Status.REJECTED]:
            actor = application.verified_by or application.updated_by
            actor_name = "an administrator"
            if actor:
                if _is_company_owner_of(actor.id, application):
                    actor_name = f"the company owner, {actor.full_name}"
                else:
                    actor_name = actor.full_name

            return CustomResponse(
                general_message=f"This mentor application has already been {application.status.lower()} by {actor_name}."
            ).get_failure_response()

        serializer = serializers.MentorVerifySerializer(
            application, data=request.data, context={"user_id": user_id}
        )
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message=f"Mentor status updated to {serializer.validated_data.get('status')} successfully."
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class MentorPublicProfileAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Public'],
        description="View a mentor's profile publicly.",
        responses={200: serializers.MentorDetailSerializer},
    )
    def get(self, request, mentor_id):
        # The public profile is identified by the UserMentor profile ID
        mentor = UserMentor.objects.filter(id=mentor_id).first()
        
        if not mentor:
            return CustomResponse(
                general_message="Mentor profile not found."
            ).get_failure_response(status_code=404)
        
        # Check if the user has any approved application
        if not MentorApplication.objects.filter(user=mentor.user, status=MentorApplication.Status.APPROVED).exists():
            return CustomResponse(general_message="This user is not an approved mentor.").get_failure_response(status_code=403)
            
        serializer = serializers.MentorDetailSerializer(mentor, context={'request': request})
        return CustomResponse(response=serializer.data).get_success_response()

class MentorChangeCompanyAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Request to change the company affiliation for a mentor. This will create a new pending mentor application for the selected company.",
        request=inline_serializer(
            name='MentorChangeCompanySerializer',
            fields={
                'company_id': rest_serializers.CharField(required=True),
                'reason': rest_serializers.CharField(required=False, allow_blank=True)
            }
        ),
        responses={200: serializers.MentorRegisterSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company_id = request.data.get('company_id')
        reason = request.data.get('reason')
        now = DateTimeUtils.get_current_utc_time()

        if not company_id:
            return CustomResponse(general_message="Company ID is required.").get_failure_response()

        new_company_org = Organization.objects.filter(id=company_id, org_type=OrganizationType.COMPANY.value).first()
        if not new_company_org:
            return CustomResponse(general_message="Invalid Company ID.").get_failure_response(status_code=404)

        if MentorApplication.objects.filter(user_id=user_id, org=new_company_org, status=MentorApplication.Status.PENDING).exists():
            return CustomResponse(general_message="You already have a pending request for this company.").get_failure_response()

        if MentorApplication.objects.filter(user_id=user_id, org=new_company_org, status=MentorApplication.Status.APPROVED).exists():
            return CustomResponse(general_message="You are already an approved mentor for this company.").get_failure_response()

        # Use the user's single UserMentor profile as the template
        existing_mentor_profile = UserMentor.objects.filter(user_id=user_id).first()
        
        if not existing_mentor_profile:
            return CustomResponse(
                general_message="Mentor profile not found. Cannot create application from template."
            ).get_failure_response(status_code=404)

        new_mentor_app = MentorApplication.objects.create(
            user_id=user_id,
            org=new_company_org,
            mentor_tier=MentorApplication.MentorTier.COMPANY_MENTOR,
            status=MentorApplication.Status.PENDING,
            about=existing_mentor_profile.about,
            expertise=existing_mentor_profile.expertise,
            hours=existing_mentor_profile.hours,
            # preferred_ig_ids are not on the UserMentor model anymore
            reason=reason,
            created_by_id=user_id,
            updated_by_id=user_id,
            created_at=now,
            updated_at=now,
        )

        # Manually trigger notification/logging logic
        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            from db.company import Company
            from db.mentor import SystemActionLog
            from django.conf import settings

            requester = User.every.filter(id=user_id).first()
            
            # Notify company owner
            try:
                company = Company.objects.get(org=new_company_org, status="verified")
                owner_user = company.company_user
                NotificationUtils.insert_notification(
                    user=owner_user,
                    title="New Mentor Application",
                    description=f"{requester.full_name} has applied to be a mentor for your company.",
                    button="View Application",
                    url=f"{settings.FR_DOMAIN_NAME}/dashboard/company/mentor/list/",
                    created_by=requester,
                )
            except Company.DoesNotExist:
                pass

            # Log for admins
            SystemActionLog.objects.create(
                action_type=SystemActionLog.ActionType.MENTOR_APP_SUBMITTED.value,
                actor_user=requester,
                subject_user=requester,
                entity_name='mentor_application',
                entity_id=new_mentor_app.id,
                new_data={'mentor_tier': new_mentor_app.mentor_tier, 'org_id': str(new_mentor_app.org.id), 'org_title': new_mentor_app.org.title, 'reason': new_mentor_app.reason},
                remarks=f"New company change request from mentor {requester.full_name} for {new_company_org.title}."
            )
        except Exception:
            pass

        serializer = serializers.MentorRegisterSerializer(new_mentor_app)
        return CustomResponse(
            general_message="Request to change company submitted successfully. It is pending approval.",
            response=serializer.data
        ).get_success_response()

class MentorOverviewAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Retrieve an overview dashboard of metrics aggregated dynamically based on the authenticated mentor's active scopes (Campus, Company, IG).",
        responses={
            200: inline_serializer(
                name='MentorOverviewData',
                fields={
                    'scopes': inline_serializer(
                        name='MentorScopeMetrics',
                        fields={
                            'scope_type': rest_serializers.CharField(),
                            'scope_id': rest_serializers.CharField(),
                            'scope_name': rest_serializers.CharField(allow_null=True),
                            'metrics': rest_serializers.DictField()
                        },
                        many=True
                    )
                }
            )
        }
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        scopes = get_mentor_overview(user_id)
        
        if not scopes:
            return CustomResponse(
                general_message="No active mentor scopes found for this user."
            ).get_failure_response(status_code=403)
            
        return CustomResponse(
            general_message="Mentor dashboard fetched successfully.",
            response={"scopes": scopes}
        ).get_success_response()


class AdminAssignMentorAPI(APIView):
    """
    Admin-only endpoint for bulk assigning / revoking mentor status.

    POST  /api/v1/mentor/admin/assign/
        Body: { user_muids, mentor_tier, [org_id], [ig_ids], [about], [expertise], [hours] }
        Assigns all listed users as mentors atomically.

    DELETE /api/v1/mentor/admin/assign/<user_muid>/
        Revokes mentor assignment for the given user.
        Optional query param ?mentor_tier=<tier> scopes revocation to a single tier.
    """
    permission_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=["Dashboard - Mentor"],
        description="Bulk assign users as mentors for a specific tier (admin only).",
        request=serializers.AdminAssignMentorSerializer,
        responses={200: None},
    )
    def post(self, request):
        admin_id = JWTUtils.fetch_user_id(request)

        ser = serializers.AdminAssignMentorSerializer(
            data=request.data,
            context={"user_id": admin_id},
        )
        if not ser.is_valid():
            return CustomResponse(message=ser.errors).get_failure_response()

        assigned_muids = ser.save()
        return CustomResponse(
            general_message="Mentors assigned successfully.",
            response={"assigned_user_muids": assigned_muids},
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=["Dashboard - Mentor"],
        description=(
            "Revoke mentor assignment for a user (admin only). "
            "Supply ?mentor_tier=<tier> to target a single tier; "
            "omit it to revoke all tiers."
        ),
        parameters=[
            OpenApiParameter(
                name="mentor_tier",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Optional tier to restrict revocation scope.",
            )
        ],
        responses={200: None},
    )
    def delete(self, request, user_muid):
        from db.user import User, UserRoleLink, Role
        from db.task import UserIgLink
        from utils.types import RoleType as _RoleType
        from django.db import transaction

        admin_id = JWTUtils.fetch_user_id(request)

        # Resolve user
        user = User.objects.filter(muid=user_muid).first()
        if not user:
            return CustomResponse(
                general_message=f"No user found with muid '{user_muid}'."
            ).get_failure_response(status_code=404)

        mentor_tier = request.query_params.get("mentor_tier")

        # Build the queryset of UserMentor records to revoke
        qs = MentorApplication.objects.filter(user=user, status=MentorApplication.Status.APPROVED)
        if mentor_tier:
            qs = qs.filter(mentor_tier=mentor_tier)

        applications = list(qs)
        if not applications:
            return CustomResponse(
                general_message="No approved mentor records found to revoke."
            ).get_failure_response(status_code=404)

        now = DateTimeUtils.get_current_utc_time()

        with transaction.atomic():
            for app in applications:
                app.status = MentorApplication.Status.REJECTED
                app.updated_by_id = admin_id
                app.updated_at = now
                app.save(update_fields=["status", "updated_by_id", "updated_at"])

                # Deactivate IG links for IG_MENTOR
                if app.mentor_tier == MentorApplication.MentorTier.IG_MENTOR:
                    UserIgLink.objects.filter(
                        user=user,
                        assignment_type=UserIgLink.AssignmentType.MENTOR,
                    ).update(is_active=False)

                # Deactivate matching scope grants. NOTE: revoking mentor
                from db.user import MentorScopeGrant
                MentorScopeGrant.objects.filter(
                    application=app, is_active=True
                ).update(
                    is_active=False,
                    revoked_by_id=admin_id,
                    revoked_at=now,
                )

            # Strip the Mentor role only if no approved mentor applications remain at all
            remaining_approved = MentorApplication.objects.filter(
                user=user, status=MentorApplication.Status.APPROVED
            ).exists()
            if not remaining_approved:
                mentor_role = Role.objects.filter(title=_RoleType.MENTOR.value).first()
                if mentor_role:
                    UserRoleLink.objects.filter(user=user, role=mentor_role).delete()

        return CustomResponse(
            general_message="Mentor assignment revoked successfully."
        ).get_success_response()


class MentorScopeGrantListAPI(APIView):
    """
    GET /mentor/<mentor_id>/grants/ — list all scope grants for a mentor.
    Admins see any mentor; a Company owner sees only their own employees'
    grants.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="List all scope grants for a mentor.",
        responses={200: serializers.MentorScopeGrantSerializer(many=True)},
    )
    def get(self, request, mentor_id):
        from db.user import MentorScopeGrant

        actor_id = JWTUtils.fetch_user_id(request)
        application = MentorApplication.objects.filter(id=mentor_id).first()
        if not application:
            return CustomResponse(
                general_message="Mentor application not found."
            ).get_failure_response(status_code=404)

        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles
        if not is_admin and not _is_company_owner_of(actor_id, application):
            return CustomResponse(
                general_message="You are not authorized to view this mentor's grants."
            ).get_failure_response(status_code=403)

        grants = MentorScopeGrant.objects.filter(application=application).order_by('-granted_at')
        serializer = serializers.MentorScopeGrantSerializer(grants, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class MentorScopeGrantRevokeAPI(APIView):
    """
    DELETE /mentor/<mentor_id>/grants/<grant_id>/ — revoke a single scope
    grant. Only ever deactivates that grant; every other grant this mentor
    holds, and their UserOrganizationLink employment record, are untouched.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Revoke a single mentor scope grant.",
        responses={200: None},
    )
    def delete(self, request, mentor_id, grant_id):
        from db.user import MentorScopeGrant

        actor_id = JWTUtils.fetch_user_id(request)
        application = MentorApplication.objects.filter(id=mentor_id).first()
        if not application:
            return CustomResponse(
                general_message="Mentor application not found."
            ).get_failure_response(status_code=404)

        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles
        if not is_admin and not _is_company_owner_of(actor_id, application):
            return CustomResponse(
                general_message="You are not authorized to revoke this mentor's grants."
            ).get_failure_response(status_code=403)

        grant = MentorScopeGrant.objects.filter(id=grant_id, application=application, is_active=True).first()
        if not grant:
            return CustomResponse(
                general_message="Active grant not found."
            ).get_failure_response(status_code=404)

        from utils.utils import DateTimeUtils
        grant.is_active = False
        grant.revoked_by_id = actor_id
        grant.revoked_at = DateTimeUtils.get_current_utc_time()
        grant.save(update_fields=["is_active", "revoked_by_id", "revoked_at"])

        # IG_MENTOR grants are the display/audit counterpart of UserIgLink,
        # the table session/task/availability endpoints actually check —
        # keep them in sync so a surgical single-IG revoke actually removes
        # that IG's mentoring capability, not just the audit-trail row.
        if grant.scope_type == MentorScopeGrant.ScopeType.IG_MENTOR and grant.scope_id:
            from db.task import UserIgLink
            UserIgLink.objects.filter(
                user=application.user,
                ig_id=grant.scope_id,
                assignment_type=UserIgLink.AssignmentType.MENTOR,
            ).update(is_active=False)

        # If this was the mentor's last active grant for its tier and no
        # other tier grant remains, the platform-wide Mentor role stays —
        # that's governed by whether any UserMentor row is still APPROVED,
        # which this grant revocation does not change.

        return CustomResponse(
            general_message="Grant revoked successfully."
        ).get_success_response()
