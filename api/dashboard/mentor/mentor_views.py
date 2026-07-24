import re
from rest_framework.views import APIView
from django.db.models import Q, Case, When
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.utils import CommonUtils
from db.user import UserMentor, Socials
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

        org_id = request.data.get('org')

        # Prevent duplicate PENDING or APPROVED applications for the same scope.
        if org_id:
            if UserMentor.objects.filter(user_id=user_id, org_id=org_id, status=UserMentor.Status.PENDING).exists():
                return CustomResponse(
                    general_message="You already have a pending mentor application for this company."
                ).get_failure_response()
            if UserMentor.objects.filter(user_id=user_id, org_id=org_id, status=UserMentor.Status.APPROVED).exists():
                return CustomResponse(
                    general_message="You are already an approved mentor for this company."
                ).get_failure_response()
        else:
            # A user can only have one pending/approved IG mentor application at a time.
            if UserMentor.objects.filter(user_id=user_id, mentor_tier=UserMentor.MentorTier.IG_MENTOR, status__in=[UserMentor.Status.PENDING, UserMentor.Status.APPROVED]).exists():
                return CustomResponse(
                    general_message="You already have an active or pending IG mentor application. You can edit your preferred IGs from your profile."
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

        mentor = UserMentor.objects.filter(user_id=user_id).first()

        if not mentor:
            return CustomResponse(
                general_message="No mentor registration request found for your account."
            ).get_failure_response(status_code=404)

        if mentor.status == UserMentor.Status.APPROVED:
            return CustomResponse(
                general_message="Your mentor application is already approved. Please use the profile endpoint to update your details."
            ).get_failure_response()

        serializer = serializers.MentorUpdateSerializer(
            mentor, data=request.data, partial=True, context={"user_id": user_id}
        )

        if serializer.is_valid():
            if 'linkedin' in serializer.validated_data:
                linkedin_url = serializer.validated_data.get('linkedin')
                socials, created = Socials.objects.get_or_create(user_id=user_id)
                socials.linkedin = linkedin_url or None
                socials.save(update_fields=['linkedin'])

            if mentor.status == UserMentor.Status.REJECTED:
                serializer.save(status=UserMentor.Status.PENDING, verification_note=None)
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
        
        mentor = UserMentor.objects.filter(user_id=user_id).first()
        if not mentor:
            return CustomResponse(
                general_message="No mentor request found for your account."
            ).get_failure_response(status_code=404)

        from .dash_mentor_helper import get_mentor_company
        organization = get_mentor_company(mentor)

        response = {
            "status": mentor.status,
            "organization": organization,
            "verified_by": getattr(mentor.verified_by, "full_name", None) if mentor.verified_by else None,
            "verified_at": mentor.verified_at,
        }

        if mentor.status == UserMentor.Status.REJECTED:
            response["rejection_reason"] = mentor.verification_note

        return CustomResponse(response=response).get_success_response()

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
        mentor = UserMentor.objects.filter(user_id=user_id, status=UserMentor.Status.APPROVED).first()
        
        if not mentor:
            return CustomResponse(
                general_message="Mentor profile not found or not approved."
            ).get_failure_response(status_code=404)

        serializer = serializers.MentorDetailSerializer(mentor)
        response_data = serializer.data

        socials = Socials.objects.filter(user_id=user_id).first()
        response_data['linkedin'] = socials.linkedin if socials else None

        return CustomResponse(response=response_data).get_success_response()

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Update the profile of a verified mentor.",
        request=serializers.MentorUpdateSerializer,
        responses={200: serializers.MentorUpdateSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        mentor = UserMentor.objects.filter(user_id=user_id, status=UserMentor.Status.APPROVED).first()
        
        if not mentor:
            return CustomResponse(
                general_message="Mentor profile not found or not approved."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.MentorUpdateSerializer(
            mentor, data=request.data, partial=True, context={"user_id": user_id}
        )
        
        if serializer.is_valid():
            general_message = "Mentor profile updated successfully."
            new_url_pending = False

            if 'linkedin' in serializer.validated_data:
                linkedin_url = serializer.validated_data.get('linkedin')
                
                if linkedin_url:
                    if UserMentor.objects.filter(user_id=user_id, status=UserMentor.Status.PENDING, about="[LinkedIn URL Update Request]").exists():
                        return CustomResponse(general_message="You already have a pending LinkedIn URL update request.").get_failure_response()
                    
                    UserMentor.objects.create(
                        user_id=user_id,
                        org=mentor.org,
                        mentor_tier=mentor.mentor_tier,
                        status=UserMentor.Status.PENDING,
                        about="[LinkedIn URL Update Request]",
                        expertise=linkedin_url,
                        reason="User requested LinkedIn URL update from profile.",
                        hours=mentor.hours,
                        preferred_ig_ids=mentor.preferred_ig_ids,
                        created_by_id=user_id,
                        updated_by_id=user_id,
                    )
                    general_message = "Profile updated. LinkedIn URL change has been submitted for verification."
                    new_url_pending = True
                else:
                    socials, _ = Socials.objects.get_or_create(user_id=user_id)
                    socials.linkedin = None
                    socials.save(update_fields=['linkedin'])
 
            serializer.save()
 
            response_serializer = serializers.MentorDetailSerializer(mentor)
            response_data = response_serializer.data
            socials = Socials.objects.filter(user_id=user_id).first()
            
            if new_url_pending:
                response_data['linkedin'] = None
            else:
                response_data['linkedin'] = socials.linkedin if socials else None

            return CustomResponse(
                general_message=general_message,
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
        mentors = UserMentor.objects.all()

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
        mentor = UserMentor.objects.filter(id=mentor_id).first()
        if not mentor:
            return CustomResponse(
                general_message="Mentor not found."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.MentorDetailSerializer(mentor)
        return CustomResponse(response=serializer.data).get_success_response()

def _is_company_owner_of(actor_id, mentor):
    """
    True if `actor_id` owns the verified Company that `mentor`'s
    COMPANY_MENTOR application is scoped to. Verification authority for a
    company's own mentor applications belongs to that company's owner, not
    only platform admins.
    """
    if mentor.mentor_tier != UserMentor.MentorTier.COMPANY_MENTOR or not mentor.org:
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
        mentor = UserMentor.objects.select_related('verified_by', 'updated_by', 'org').filter(id=mentor_id).first()

        if not mentor:
            return CustomResponse(
                general_message="Mentor request not found."
            ).get_failure_response(status_code=404)

        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles
        is_owner = _is_company_owner_of(user_id, mentor)

        # Authorization check
        can_verify = False
        if mentor.mentor_tier == UserMentor.MentorTier.COMPANY_MENTOR:
            # For company mentors, both admin and owner can verify
            if is_admin or is_owner:
                can_verify = True
        else:
            # For other tiers (like IG_MENTOR), only admin can verify
            if is_admin:
                can_verify = True
        
        if not can_verify:
            return CustomResponse(
                general_message="You are not authorized to verify this mentor application."
            ).get_failure_response(status_code=403)

        if mentor.status in [UserMentor.Status.APPROVED, UserMentor.Status.REJECTED]:
            actor = mentor.verified_by or mentor.updated_by
            actor_name = "an administrator"
            if actor:
                if _is_company_owner_of(actor.id, mentor):
                    actor_name = f"the company owner, {actor.full_name}"
                else:
                    actor_name = actor.full_name

            return CustomResponse(
                general_message=f"This mentor application has already been {mentor.status.lower()} by {actor_name}."
            ).get_failure_response()

        serializer = serializers.MentorVerifySerializer(
            mentor, data=request.data, context={"user_id": user_id}
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
        mentor = UserMentor.objects.filter(id=mentor_id, status=UserMentor.Status.APPROVED).first()
        
        if not mentor:
            return CustomResponse(
                general_message="Mentor profile not found or not approved."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.MentorDetailSerializer(mentor)
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

        if not company_id:
            return CustomResponse(general_message="Company ID is required.").get_failure_response()

        new_company_org = Organization.objects.filter(id=company_id, org_type=OrganizationType.COMPANY.value).first()
        if not new_company_org:
            return CustomResponse(general_message="Invalid Company ID.").get_failure_response(status_code=404)

        if UserMentor.objects.filter(user_id=user_id, org=new_company_org, status=UserMentor.Status.PENDING).exists():
            return CustomResponse(general_message="You already have a pending request for this company.").get_failure_response()

        if UserMentor.objects.filter(user_id=user_id, org=new_company_org, status=UserMentor.Status.APPROVED).exists():
            return CustomResponse(general_message="You are already an approved mentor for this company.").get_failure_response()

        # Prioritize the most recently updated approved profile as the source for user's data.
        existing_mentor_profile = UserMentor.objects.filter(
            user_id=user_id,
            status=UserMentor.Status.APPROVED
        ).order_by('-updated_at').first()
        
        if not existing_mentor_profile:
            # Fallback to any profile if no approved one exists (e.g., only rejected/pending applications).
            existing_mentor_profile = UserMentor.objects.filter(user_id=user_id).order_by('-updated_at').first()

        new_mentor_app = UserMentor.objects.create(
            user_id=user_id,
            org=new_company_org,
            mentor_tier=UserMentor.MentorTier.COMPANY_MENTOR,
            status=UserMentor.Status.PENDING,
            about=existing_mentor_profile.about if existing_mentor_profile else None,
            expertise=existing_mentor_profile.expertise if existing_mentor_profile else None,
            hours=existing_mentor_profile.hours if existing_mentor_profile else None,
            preferred_ig_ids=existing_mentor_profile.preferred_ig_ids if existing_mentor_profile else None,
            reason=reason,
            created_by_id=user_id,
            updated_by_id=user_id,
        )

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
        qs = UserMentor.objects.filter(user=user, status=UserMentor.Status.APPROVED)
        if mentor_tier:
            qs = qs.filter(mentor_tier=mentor_tier)

        records = list(qs)
        if not records:
            return CustomResponse(
                general_message="No approved mentor records found to revoke."
            ).get_failure_response(status_code=404)

        now = None
        try:
            from utils.utils import DateTimeUtils as _DTU
            now = _DTU.get_current_utc_time()
        except Exception:
            from django.utils import timezone
            now = timezone.now()

        with transaction.atomic():
            for record in records:
                record.status = UserMentor.Status.REJECTED
                record.updated_by_id = admin_id
                record.updated_at = now
                record.save(update_fields=["status", "updated_by_id", "updated_at"])

                # Deactivate IG links for IG_MENTOR
                if record.mentor_tier == UserMentor.MentorTier.IG_MENTOR:
                    UserIgLink.objects.filter(
                        user=user,
                        assignment_type=UserIgLink.AssignmentType.MENTOR,
                    ).update(is_active=False)

                # Deactivate matching scope grants. NOTE: revoking mentor
                # authority must never touch UserOrganizationLink — that's
                # the user's employment/identity record, not a permission.
                from db.user import MentorScopeGrant
                MentorScopeGrant.objects.filter(
                    mentor=record, is_active=True
                ).update(
                    is_active=False,
                    revoked_by_id=admin_id,
                    revoked_at=now,
                )

            # Strip the Mentor role only if no approved mentor records remain at all
            remaining_approved = UserMentor.objects.filter(
                user=user, status=UserMentor.Status.APPROVED
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
        mentor = UserMentor.objects.filter(id=mentor_id).first()
        if not mentor:
            return CustomResponse(
                general_message="Mentor not found."
            ).get_failure_response(status_code=404)

        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles
        if not is_admin and not _is_company_owner_of(actor_id, mentor):
            return CustomResponse(
                general_message="You are not authorized to view this mentor's grants."
            ).get_failure_response(status_code=403)

        grants = MentorScopeGrant.objects.filter(mentor=mentor).order_by('-granted_at')
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
        mentor = UserMentor.objects.filter(id=mentor_id).first()
        if not mentor:
            return CustomResponse(
                general_message="Mentor not found."
            ).get_failure_response(status_code=404)

        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles
        if not is_admin and not _is_company_owner_of(actor_id, mentor):
            return CustomResponse(
                general_message="You are not authorized to revoke this mentor's grants."
            ).get_failure_response(status_code=403)

        grant = MentorScopeGrant.objects.filter(id=grant_id, mentor=mentor, is_active=True).first()
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
                user=mentor.user,
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
