import re
from datetime import timedelta
from rest_framework.views import APIView
from django.db.models import Q, Case, When
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.utils import CommonUtils, DateTimeUtils
from db.user import UserMentor, Socials, MentorApplication, MentorScopeGrant
from db.mentor import MentorshipSession
from db.organization import Organization
from db.task import KarmaActivityLog
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, inline_serializer
from django.db import transaction
from rest_framework import serializers as rest_serializers
from . import serializers
from .dash_mentor_helper import get_mentor_overview, get_mentor_scopes, is_mentor_active

NOMINATION_EXPIRY_DAYS = 14


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

        applications = MentorApplication.objects.filter(user_id=user_id).select_related('org', 'verified_by').order_by('-created_at')
        if not applications.exists():
            return CustomResponse(
                general_message="No mentor requests found for your account."
            ).get_failure_response(status_code=404)

        latest = applications.first()

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

        # Sort activities by date descending. Fall back to a timezone-aware
        # min datetime (not "") so a missing date never gets compared against
        # a datetime, which would raise TypeError.
        from django.utils import timezone
        from datetime import datetime as _datetime
        _min_date = _datetime.min.replace(tzinfo=timezone.get_current_timezone())
        activities.sort(key=lambda x: x["date"] or _min_date, reverse=True)

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
    """
    Admin review queue over MentorApplication rows — pending applications by
    default, filterable to any status/tier. This is distinct from the
    roster of currently-active mentors (see MentorRosterAPI), since a tier's
    membership is no longer stored on a single reviewable row.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="List mentor applications with filtering.",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("mentor_tier", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: serializers.MentorApplicationListSerializer(many=True)},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        # A PENDING application is a "change request" (shown only under
        # change-requests/) only when the same user already holds an
        # APPROVED application of the *same tier* — e.g. an approved IG
        # mentor re-applying for IG_MENTOR at a different org. A PENDING
        # application for a *different* tier (e.g. an approved IG mentor
        # newly applying for CAMPUS_MENTOR) is a genuinely new application
        # and must still show up in the main review queue.
        approved_user_tier_pairs = set(
            MentorApplication.objects.filter(
                status=MentorApplication.Status.APPROVED
            ).values_list('user_id', 'mentor_tier')
        )

        applications = MentorApplication.objects.select_related('user')
        if approved_user_tier_pairs:
            change_request_ids = [
                app.id for app in applications.filter(status=MentorApplication.Status.PENDING)
                if (app.user_id, app.mentor_tier) in approved_user_tier_pairs
            ]
            if change_request_ids:
                applications = applications.exclude(id__in=change_request_ids)

        status = request.query_params.get("status")
        mentor_tier = request.query_params.get("mentor_tier")

        if status:
            applications = applications.filter(status=status)
        if mentor_tier:
            applications = applications.filter(mentor_tier=mentor_tier)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            applications, request,
            search_fields=["user__full_name", "user__email"],
            sort_fields={"created_at": "created_at", "status": "status", "user_full_name": "user__full_name"}
        )

        serializer = serializers.MentorApplicationListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class MentorRosterAPI(APIView):
    """
    Admin roster of currently-active mentors, i.e. users holding at least
    one active MentorScopeGrant, optionally filtered to a single tier.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="List active mentors (users holding at least one active tier grant).",
        parameters=[
            OpenApiParameter("mentor_tier", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("low_rating", OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=False,
                              description="Surface mentors averaging below 3.0 across >= 5 rated sessions."),
        ],
        responses={200: serializers.MentorDetailSerializer(many=True)},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        mentor_tier = request.query_params.get("mentor_tier")
        low_rating = request.query_params.get("low_rating", "").lower() == "true"

        mentor_user_ids = MentorScopeGrant.objects.filter(
            is_active=True, application__status=MentorApplication.Status.APPROVED,
        )
        if mentor_tier:
            mentor_user_ids = mentor_user_ids.filter(scope_type=mentor_tier)
        mentor_user_ids = mentor_user_ids.values_list('application__user_id', flat=True).distinct()

        mentors = UserMentor.objects.filter(user_id__in=mentor_user_ids, is_active=True)

        if low_rating:
            from django.db.models import Avg, Count
            from db.mentor import MentorshipSessionUserLink
            # Ratings live on the MENTEE's own participant link (a mentee
            # rates the mentor who ran the session), so group by the
            # session's creator — the mentor — rather than by the (never
            # rating-bearing) MENTOR-role link's own user_id.
            low_rated_user_ids = (
                MentorshipSessionUserLink.objects.filter(
                    participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
                    rating__isnull=False,
                )
                .values('session__created_by_id')
                .annotate(avg_rating=Avg('rating'), rating_count=Count('id'))
                .filter(avg_rating__lt=3.0, rating_count__gte=5)
                .values_list('session__created_by_id', flat=True)
            )
            mentors = mentors.filter(user_id__in=list(low_rated_user_ids))

        paginated_queryset = CommonUtils.get_paginated_queryset(
            mentors, request,
            search_fields=["user__full_name", "user__email"],
            sort_fields={"created_at": "created_at", "user_full_name": "user__full_name"}
        )

        serializer = serializers.MentorDetailSerializer(paginated_queryset.get("queryset"), many=True)
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
        description="Get details of a specific mentor application by ID.",
        responses={200: serializers.MentorApplicationListSerializer},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request, mentor_id):
        application = MentorApplication.objects.filter(id=mentor_id).first()
        if not application:
            return CustomResponse(
                general_message="Mentor application not found."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.MentorApplicationListSerializer(application)
        return CustomResponse(response=serializer.data).get_success_response()

class MentorChangeRequestListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="List all mentor company change applications for admin review.",
        responses={200: serializers.MentorApplicationListSerializer(many=True)},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        # A change request is a PENDING application whose user already holds
        # an APPROVED application of the *same* tier (see MentorListAPI for
        # the matching exclusion logic this must stay consistent with).
        approved_user_tier_pairs = set(
            MentorApplication.objects.filter(
                status=MentorApplication.Status.APPROVED
            ).values_list('user_id', 'mentor_tier')
        )

        pending_applications = MentorApplication.objects.select_related('user').filter(
            status=MentorApplication.Status.PENDING
        )
        change_request_ids = [
            app.id for app in pending_applications
            if (app.user_id, app.mentor_tier) in approved_user_tier_pairs
        ]
        change_requests = pending_applications.filter(id__in=change_request_ids)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            change_requests, request, 
            search_fields=["user__full_name", "user__email"],
            sort_fields={"created_at": "created_at", "user_full_name": "user__full_name"}
        )
        
        serializer = serializers.MentorApplicationListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={"data": serializer.data, "pagination": paginated_queryset.get("pagination")}
        ).get_success_response()

def _is_company_owner_of(actor_id, mentor):
    """
    True if `actor_id` owns the verified Company that `mentor`'s COMPANY_MENTOR
    application is scoped to, or is an accepted delegate. Verification
    authority for a company's own mentor applications belongs to that
    company's owner or delegate, not only platform admins.
    """
    if mentor.mentor_tier != MentorApplication.MentorTier.COMPANY_MENTOR or not mentor.org:
        return False

    from db.company import Company, CompanyAdminLink
    company = Company.objects.filter(
        org=mentor.org,
        status="verified",
    ).first()

    if not company:
        return False

    # Check if actor is the owner
    if company.company_user_id == actor_id:
        return True

    # Check if actor is an accepted delegate
    return CompanyAdminLink.objects.filter(
        company=company,
        user_id=actor_id,
        status='Accepted'
    ).exists()


def _is_ig_lead_of(actor_id, application):
    """
    True if `actor_id` holds the IGLead role for at least one of `application`'s
    preferred IGs. Lets an IG's own lead verify an IG_MENTOR application for
    that IG, alongside (not instead of) platform admins.
    """
    if application.mentor_tier != MentorApplication.MentorTier.IG_MENTOR:
        return False

    ig_ids = application.preferred_ig_ids or []
    if not ig_ids:
        return False

    from db.task import InterestGroup
    from db.user import UserRoleLink
    lead_role_titles = InterestGroup.objects.filter(id__in=ig_ids).values_list('code', flat=True)
    lead_role_titles = [RoleType.IG_LEAD_ROLE(code) for code in lead_role_titles]
    if not lead_role_titles:
        return False

    return UserRoleLink.objects.filter(
        user_id=actor_id, role__title__in=lead_role_titles,
    ).exists()


class MentorVerifyAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description=(
            "Verify or reject a mentor application. Platform admins can "
            "verify any application EXCEPT COMPANY_MENTOR, which is verified "
            "solely by the target company's owner — unless that company has "
            "no verified owner to act (deactivated, rejected, or never "
            "existed), in which case a platform admin may step in."
        ),
        request=serializers.MentorVerifySerializer,
    )
    def patch(self, request, mentor_id):
        user_id = JWTUtils.fetch_user_id(request)
        application = MentorApplication.objects.select_related('verified_by', 'updated_by', 'org').filter(id=mentor_id).first()

        if not application:
            return CustomResponse(
                general_message="Mentor application not found."
            ).get_failure_response(status_code=404)

        if application.user_id == user_id:
            return CustomResponse(
                general_message="You cannot verify your own mentor application."
            ).get_failure_response(status_code=403)

        roles = JWTUtils.fetch_role(request)
        is_admin = RoleType.ADMIN.value in roles
        is_owner = _is_company_owner_of(user_id, application)
        is_ig_lead = _is_ig_lead_of(user_id, application)

        # Authorization check
        can_verify = False
        if application.mentor_tier == MentorApplication.MentorTier.COMPANY_MENTOR:
            # For company mentors, the company owner is normally the sole
            # verifier. But if the target company has no verified owner to
            # act (deactivated, rejected, or never existed), the application
            # would otherwise be permanently unverifiable — fall back to
            # platform admin authority in that case.
            if is_owner:
                can_verify = True
            elif is_admin:
                from db.company import Company
                has_verified_company = bool(
                    application.org_id and Company.objects.filter(org_id=application.org_id, status="verified").exists()
                )
                can_verify = not has_verified_company
        elif application.mentor_tier == MentorApplication.MentorTier.IG_MENTOR:
            # Either the IG's own lead, or a platform admin, can verify.
            can_verify = is_admin or is_ig_lead
        else:
            can_verify = is_admin

        if not can_verify:
            return CustomResponse(
                general_message="You are not authorized to verify this mentor application."
            ).get_failure_response(status_code=403)

        # Lock the row and re-check status under the lock so two concurrent
        # verifiers (e.g. an admin and an IG lead) can't both approve/reject
        # the same application.
        with transaction.atomic():
            application = MentorApplication.objects.select_for_update().select_related(
                'verified_by', 'updated_by', 'org'
            ).get(id=mentor_id)

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

            if not serializer.is_valid():
                return CustomResponse(message=serializer.errors).get_failure_response()

            updated_status = serializer.validated_data.get('status')
            serializer.save()

        return CustomResponse(
            general_message=f"Mentor status updated to {updated_status} successfully."
        ).get_success_response()

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
        description=(
            "Request to change the primary organizational affiliation for an existing mentor. "
            "Creates a new PENDING application for the selected organization, preserving the "
            "original mentor tier. The mentor's current approved application/authority for their "
            "existing organization stays active and is only revoked once the new application is "
            "approved (so there is no gap in authority while the change request is pending). "
            "If the new application is rejected instead, the existing affiliation is unaffected."
        ),
        request=inline_serializer(
            name='MentorChangeOrgSerializer',
            fields={
                'org_id': rest_serializers.CharField(required=True),
                'reason': rest_serializers.CharField(required=False, allow_blank=True)
            }
        ),
        responses={200: serializers.MentorRegisterSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        org_id = request.data.get('org_id')
        reason = request.data.get('reason')
        now = DateTimeUtils.get_current_utc_time()

        if not org_id:
            return CustomResponse(general_message="Organization ID is required.").get_failure_response()

        new_org = Organization.objects.filter(id=org_id).first()
        if not new_org:
            return CustomResponse(general_message="Invalid Organization ID.").get_failure_response(status_code=404)

        # Find the user's latest approved mentor application to determine their current tier.
        latest_approved_app = MentorApplication.objects.filter(
            user_id=user_id,
            status=MentorApplication.Status.APPROVED
        ).order_by('-created_at').first()

        if not latest_approved_app:
            return CustomResponse(
                general_message="You must have an approved mentor application to change your affiliation."
            ).get_failure_response(status_code=403)

        # Preserve the mentor's tier from their existing approved application.
        new_mentor_tier = latest_approved_app.mentor_tier

        if MentorApplication.objects.filter(user_id=user_id, org=new_org, mentor_tier=new_mentor_tier, status__in=[MentorApplication.Status.PENDING, MentorApplication.Status.APPROVED]).exists():
            return CustomResponse(general_message="You already have an active or pending application for this organization.").get_failure_response()

        # Use the user's single UserMentor profile as the template
        existing_mentor_profile = UserMentor.objects.filter(user_id=user_id).first()
        
        if not existing_mentor_profile:
            return CustomResponse(
                general_message="Mentor profile not found. Cannot create application from template."
            ).get_failure_response(status_code=404)

        new_mentor_app = MentorApplication.objects.create(
            user_id=user_id,
            org=new_org,
            mentor_tier=new_mentor_tier,
            status=MentorApplication.Status.PENDING,
            preferred_ig_ids=latest_approved_app.preferred_ig_ids if latest_approved_app else None,
            reason=reason,
            nomination_expires_at=now + timedelta(days=NOMINATION_EXPIRY_DAYS),
            created_by_id=user_id,
            updated_by_id=user_id,
            created_at=now,
            updated_at=now,
        )

        # Manually trigger notification/logging logic
        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User, UserRoleLink
            from db.company import Company
            from db.mentor import SystemActionLog
            from django.conf import settings

            requester = User.every.filter(id=user_id).first()
            
            if new_mentor_tier == MentorApplication.MentorTier.COMPANY_MENTOR:
                # Notify company owner
                try:
                    company = Company.objects.get(org=new_org, status="verified")
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
                    new_data={
                        'mentor_tier': new_mentor_app.mentor_tier,
                        'org_id': str(new_mentor_app.org.id),
                        'org_title': new_mentor_app.org.title,
                        'reason': new_mentor_app.reason,
                        'previous_org_id': str(latest_approved_app.org.id) if latest_approved_app.org else None,
                        'previous_org_title': latest_approved_app.org.title if latest_approved_app.org else None,
                        'previous_app_id': str(latest_approved_app.id),
                    },
                    remarks=f"Mentor {requester.full_name} requested to change affiliation from {latest_approved_app.org.title if latest_approved_app.org else 'N/A'} to {new_org.title} (pending approval)."
                )
            elif new_mentor_tier == MentorApplication.MentorTier.CAMPUS_MENTOR:
                # Notify admins for Campus Mentor affiliation changes
                admin_roles = UserRoleLink.objects.filter(role__title=RoleType.ADMIN.value, is_active=True).select_related('user')
                for admin_link in admin_roles:
                    NotificationUtils.insert_notification(
                        user=admin_link.user,
                        title="New Campus Mentor Affiliation Request",
                        description=f"Mentor {requester.full_name} has requested to change campus affiliation to {new_org.title}.",
                        button="View Application",
                        url=f"{settings.FR_DOMAIN_NAME}/dashboard/mentor/list/",
                        created_by=requester,
                    )
            elif new_mentor_tier == MentorApplication.MentorTier.IG_MENTOR:
                # Notify admins
                admin_roles = UserRoleLink.objects.filter(role__title=RoleType.ADMIN.value, is_active=True).select_related('user')
                for admin_link in admin_roles:
                    NotificationUtils.insert_notification(
                        user=admin_link.user,
                        title="IG Mentor Affiliation Change Request",
                        description=f"IG Mentor {requester.full_name} has requested to change affiliation to {new_org.title}.",
                        button="View Application",
                        url=f"{settings.FR_DOMAIN_NAME}/dashboard/mentor/list/",
                        created_by=requester,
                    )
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Failed to notify/log mentor org-change request for application %s", new_mentor_app.id
            )

        serializer = serializers.MentorRegisterSerializer(new_mentor_app)
        return CustomResponse(
            general_message=f"Request to change affiliation to {new_org.title} submitted successfully. It is pending approval.",
            response=serializer.data
        ).get_success_response()

class MentorPreferredIgAPI(APIView):
    """
    GET/PATCH /mentor/<mentor_id>/preferred-igs/ — self-service request to
    add/remove the Interest Groups a mentor mentors under one of their own
    APPROVED applications. Registration (MentorRegistrationAPI) only accepts
    preferred_ig_ids while PENDING/REJECTED; MentorRegistrationAPI.patch
    explicitly refuses to touch an APPROVED application at all. This is the
    endpoint that fills that gap — but rather than mutating the approved
    application's IGs in place, PATCH creates a new PENDING "change request"
    application (mirroring MentorChangeCompanyAPI) so the change goes
    through the same verifier who'd review it normally: an IG lead/admin for
    IG_MENTOR, the company owner for COMPANY_MENTOR, admins for CAMPUS_MENTOR.
    The mentor's current IG access is untouched until that's approved.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Get the preferred Interest Groups for one of the caller's approved mentor applications.",
        responses={200: serializers.MentorApplicationProfileSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request, mentor_id):
        user_id = JWTUtils.fetch_user_id(request)
        application = MentorApplication.objects.filter(
            id=mentor_id, user_id=user_id, status=MentorApplication.Status.APPROVED
        ).first()

        if not application:
            return CustomResponse(
                general_message="No approved mentor application found with this ID for your account."
            ).get_failure_response(status_code=404)

        serializer = serializers.MentorApplicationProfileSerializer(application)
        return CustomResponse(response=serializer.data).get_success_response()

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description=(
            "Request a change to the preferred Interest Groups for one of the caller's "
            "approved mentor applications. Creates a new PENDING application (preserving "
            "the tier and org) for review by the appropriate verifier — the mentor's "
            "current IG access is unaffected until it's approved."
        ),
        request=serializers.MentorIgPreferenceSerializer,
        responses={200: serializers.MentorRegisterSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def patch(self, request, mentor_id):
        user_id = JWTUtils.fetch_user_id(request)
        application = MentorApplication.objects.filter(
            id=mentor_id, user_id=user_id, status=MentorApplication.Status.APPROVED
        ).first()

        if not application:
            return CustomResponse(
                general_message="No approved mentor application found with this ID for your account."
            ).get_failure_response(status_code=404)

        serializer = serializers.MentorIgPreferenceSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        new_ig_ids = serializer.validated_data["preferred_ig_ids"]

        if set(new_ig_ids) == set(application.preferred_ig_ids or []):
            return CustomResponse(
                general_message="No change — these are already the active Interest Groups for this application."
            ).get_failure_response()

        if MentorApplication.objects.filter(
            user_id=user_id, mentor_tier=application.mentor_tier,
            status=MentorApplication.Status.PENDING,
        ).exists():
            return CustomResponse(
                general_message="You already have a pending change request for this mentor tier."
            ).get_failure_response()

        from .dash_mentor_helper import get_effective_ig_ids, MAX_PREFERRED_IGS
        effective = get_effective_ig_ids(
            application.user, new_ig_ids, exclude_application_id=application.id
        )
        if len(effective) > MAX_PREFERRED_IGS:
            return CustomResponse(
                general_message=(
                    f"This change would give you {len(effective)} active Interest Groups, "
                    f"exceeding the maximum of {MAX_PREFERRED_IGS}."
                )
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        new_application = MentorApplication.objects.create(
            user_id=user_id,
            org=application.org,
            mentor_tier=application.mentor_tier,
            status=MentorApplication.Status.PENDING,
            preferred_ig_ids=new_ig_ids,
            reason=f"Interest Group preference change requested (supersedes application {application.id}).",
            nomination_expires_at=now + timedelta(days=NOMINATION_EXPIRY_DAYS),
            created_by_id=user_id,
            updated_by_id=user_id,
            created_at=now,
            updated_at=now,
        )

        # Notify whoever verifies this tier — same routing as initial registration.
        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User, UserRoleLink
            from django.conf import settings

            requester = User.every.filter(id=user_id).first()

            if application.mentor_tier == MentorApplication.MentorTier.COMPANY_MENTOR:
                from db.company import Company
                try:
                    company = Company.objects.get(org=application.org, status="verified")
                    NotificationUtils.insert_notification(
                        user=company.company_user,
                        title="Mentor Interest Group Change Request",
                        description=f"{requester.full_name} has requested to change their Interest Groups as a mentor for your company.",
                        button="View Application",
                        url=f"{settings.FR_DOMAIN_NAME}/dashboard/company/mentor/list/",
                        created_by=requester,
                    )
                except Company.DoesNotExist:
                    pass
            elif application.mentor_tier == MentorApplication.MentorTier.IG_MENTOR:
                from db.task import InterestGroup
                from .dash_mentor_helper import notify_ig_leads
                for ig in InterestGroup.objects.filter(id__in=new_ig_ids):
                    notify_ig_leads(ig, requester, new_application)

                admin_roles = UserRoleLink.objects.filter(role__title=RoleType.ADMIN.value, is_active=True).select_related('user')
                for admin_link in admin_roles:
                    NotificationUtils.insert_notification(
                        user=admin_link.user,
                        title="IG Mentor Preference Change Request",
                        description=f"{requester.full_name} has requested to change their Interest Groups.",
                        button="View Application",
                        url=f"{settings.FR_DOMAIN_NAME}/dashboard/mentor/list/",
                        created_by=requester,
                    )
            else:  # CAMPUS_MENTOR — admin-reviewed, same as initial registration
                admin_roles = UserRoleLink.objects.filter(role__title=RoleType.ADMIN.value, is_active=True).select_related('user')
                for admin_link in admin_roles:
                    NotificationUtils.insert_notification(
                        user=admin_link.user,
                        title="Mentor Interest Group Change Request",
                        description=f"{requester.full_name} has requested to change their Interest Groups.",
                        button="View Application",
                        url=f"{settings.FR_DOMAIN_NAME}/dashboard/mentor/list/",
                        created_by=requester,
                    )
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Failed to notify verifier for IG preference change application %s", new_application.id
            )

        response_serializer = serializers.MentorRegisterSerializer(new_application)
        return CustomResponse(
            general_message="Interest Group change request submitted successfully. It is pending approval.",
            response=response_serializer.data
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


class PersonaCurrentAPI(APIView):
    """
    GET persona/current/ — the caller's active persona/scope plus the list
    of scopes they're eligible to switch into (their active grants).
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Get the caller's active persona/scope and available mentor scopes.",
    )
    def get(self, request):
        from db.user import UserSettings

        user_id = JWTUtils.fetch_user_id(request)
        settings_row = UserSettings.objects.filter(user_id=user_id).first()

        active_persona = settings_row.active_persona if settings_row else 'learner'
        active_scope_type = settings_row.active_scope_type if settings_row else None
        active_scope_id = settings_row.active_scope_id if settings_row else None

        available_scopes = list(
            MentorScopeGrant.objects.filter(
                application__user_id=user_id,
                application__status=MentorApplication.Status.APPROVED,
                application__user__mentor_profile__is_active=True,
                is_active=True,
            ).values('scope_type', 'scope_id')
        )

        return CustomResponse(response={
            "active_persona": active_persona,
            "active_scope_type": active_scope_type,
            "active_scope_id": active_scope_id,
            "available_scopes": available_scopes,
        }).get_success_response()


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
        from db.user import MentorScopeGrant
        from utils.types import RoleType as _RoleType
        from django.db import transaction

        admin_id = JWTUtils.fetch_user_id(request)

        user = User.objects.filter(muid=user_muid).first()
        if not user:
            return CustomResponse(
                general_message=f"No user found with muid '{user_muid}'."
            ).get_failure_response(status_code=404)

        mentor = UserMentor.objects.filter(user=user).first()
        if not mentor:
            return CustomResponse(
                general_message="No mentor profile found for this user."
            ).get_failure_response(status_code=404)

        mentor_tier = request.query_params.get("mentor_tier")

        # Build the queryset of UserMentor records to revoke
        qs = MentorApplication.objects.filter(user=user, status=MentorApplication.Status.APPROVED)
        if mentor_tier:
            qs = qs.filter(mentor_tier=mentor_tier)

        applications = list(qs)
        if not applications:
            return CustomResponse(
                general_message="No active mentor grants found to revoke."
            ).get_failure_response(status_code=404)

        now = DateTimeUtils.get_current_utc_time()

        with transaction.atomic():
            for app in applications:
                # GRANT_REVOKED (not REJECTED) — this is an admin revoking an
                # already-approved grant, not a review-stage rejection. Using
                # REJECTED would let the user "fix and resubmit" this back to
                # PENDING via MentorRegistrationAPI.patch, defeating the revoke.
                app.status = MentorApplication.Status.GRANT_REVOKED
                app.updated_by_id = admin_id
                app.updated_at = now
                app.save(update_fields=["status", "updated_by_id", "updated_at"])

                # Release IG links this application held — but only the ones no
                # OTHER still-APPROVED application (e.g. a COMPANY_MENTOR app
                # that separately lists the same IG) is still relying on.
                if app.mentor_tier == MentorApplication.MentorTier.IG_MENTOR and app.preferred_ig_ids:
                    from .dash_mentor_helper import release_mentor_ig_links
                    release_mentor_ig_links(
                        user, app.preferred_ig_ids,
                        exclude_application_id=app.id, actor_user_id=admin_id,
                    )

                # Deactivate matching scope grants. NOTE: revoking mentor
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
    DELETE /mentor/<mentor_id>/grants/<grant_id>/ — revoke a mentor scope
    grant. Per product decision, revoking ANY grant on an application rejects
    the whole application (status -> GRANT_REVOKED) and deactivates every
    other active grant tied to it too — a mentor's authority under a given
    application is all-or-nothing, not per-grant. The mentor's
    UserOrganizationLink employment record is left untouched.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description=(
            "Revoke a mentor scope grant. This rejects the entire parent "
            "application and deactivates all of its other active grants too "
            "— revocation is all-or-nothing per application, not per grant."
        ),
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
        
        with transaction.atomic():
            now = DateTimeUtils.get_current_utc_time()

            # Per user feedback, revoking any grant associated with an application
            # should reject the application itself and clean up all related grants.
            
            # 1. Update parent application status to reflect grant revocation.
            application.status = MentorApplication.Status.GRANT_REVOKED
            application.updated_by_id = actor_id
            application.updated_at = now
            application.verification_note = "A mentor grant was revoked, setting the application status to Grant Revoked."
            application.save(update_fields=["status", "updated_by_id", "updated_at", "verification_note"])

            # 2. Find all active grants associated with this now-rejected application.
            all_active_grants = MentorScopeGrant.objects.filter(application=application, is_active=True)

            # 3. Find all IG-related grants among them to clean up UserIgLink.
            ig_scope_ids_to_deactivate = all_active_grants.filter(
                scope_type=MentorScopeGrant.ScopeType.IG_MENTOR
            ).values_list('scope_id', flat=True)

            if ig_scope_ids_to_deactivate:
                # Only release IGs no OTHER still-APPROVED application (e.g. a
                # separate COMPANY_MENTOR app listing the same IG) still relies on.
                from .dash_mentor_helper import release_mentor_ig_links
                release_mentor_ig_links(
                    application.user, list(ig_scope_ids_to_deactivate),
                    exclude_application_id=application.id, actor_user_id=actor_id,
                )

            # 4. Deactivate all grants for this application.
            all_active_grants.update(is_active=False, revoked_by_id=actor_id, revoked_at=now)

            # 5. If the user has no other approved mentor applications, revoke the global MENTOR role.
            if not MentorApplication.objects.filter(user=application.user, status=MentorApplication.Status.APPROVED).exists():
                from db.user import Role, UserRoleLink
                if mentor_role := Role.objects.filter(title=RoleType.MENTOR.value).first():
                    UserRoleLink.objects.filter(user=application.user, role=mentor_role).delete()

        return CustomResponse(
            general_message="Grant revoked successfully. The associated application has been rejected."
        ).get_success_response()
