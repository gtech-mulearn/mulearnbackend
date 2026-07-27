import re
from datetime import timedelta
from rest_framework.views import APIView
from django.db.models import Q, Case, When
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.utils import CommonUtils, DateTimeUtils
from db.user import UserMentor, MentorApplication, MentorScopeGrant, Socials
from db.mentor import MentorshipSession
from db.organization import Organization
from db.task import KarmaActivityLog
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, inline_serializer
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

        org_id = request.data.get('org')

        # Prevent duplicate PENDING applications for the same scope, and
        # re-applying for a scope already actively granted.
        if org_id:
            if MentorApplication.objects.filter(user_id=user_id, org_id=org_id, status=MentorApplication.Status.PENDING).exists():
                return CustomResponse(
                    general_message="You already have a pending mentor application for this company."
                ).get_failure_response()
            if MentorScopeGrant.objects.filter(
                mentor__user_id=user_id, scope_type=UserMentor.MentorTier.COMPANY_MENTOR,
                scope_id=org_id, is_active=True,
            ).exists():
                return CustomResponse(
                    general_message="You are already an approved mentor for this company."
                ).get_failure_response()
        else:
            # A user can only have one pending IG mentor application at a time.
            if MentorApplication.objects.filter(
                user_id=user_id, tier=UserMentor.MentorTier.IG_MENTOR,
                status=MentorApplication.Status.PENDING,
            ).exists():
                return CustomResponse(
                    general_message="You already have a pending IG mentor application. You can edit your preferred IGs from your profile once approved."
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

        application = MentorApplication.objects.filter(
            user_id=user_id
        ).exclude(status=MentorApplication.Status.APPROVED).order_by('-created_at').first()

        if not application:
            return CustomResponse(
                general_message="No pending or rejected mentor application found for your account."
            ).get_failure_response(status_code=404)

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
                serializer.save(
                    status=MentorApplication.Status.PENDING,
                    verification_note=None,
                    nomination_expires_at=DateTimeUtils.get_current_utc_time() + timedelta(days=NOMINATION_EXPIRY_DAYS),
                )
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
                general_message="No mentor request found for your account."
            ).get_failure_response(status_code=404)

        latest = applications.first()

        from .dash_mentor_helper import get_mentor_company
        mentor = UserMentor.objects.filter(user_id=user_id).first()
        organization = get_mentor_company(mentor) if mentor else None

        response = {
            "status": latest.status,
            "tier": latest.tier,
            "organization": organization,
            "active_tiers": sorted({scope_type for scope_type, _ in get_mentor_scopes(user_id)}),
            "verified_by": getattr(latest.verified_by, "full_name", None) if latest.verified_by else None,
            "verified_at": latest.verified_at,
            "applications": serializers.MentorApplicationListSerializer(applications, many=True).data,
        }

        if latest.status == MentorApplication.Status.REJECTED:
            response["rejection_reason"] = latest.verification_note

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
        mentor = UserMentor.objects.filter(user_id=user_id, is_active=True).first()

        if not mentor or not get_mentor_scopes(user_id):
            return CustomResponse(
                general_message="Mentor profile not found or not approved."
            ).get_failure_response(status_code=404)

        serializer = serializers.MentorProfileSerializer(mentor)
        response_data = serializer.data

        socials = Socials.objects.filter(user_id=user_id).first()
        response_data['linkedin'] = socials.linkedin if socials else None

        return CustomResponse(response=response_data).get_success_response()

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Update the profile of a verified mentor.",
        request=serializers.MentorProfileSerializer,
        responses={200: serializers.MentorProfileSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        mentor = UserMentor.objects.filter(user_id=user_id, is_active=True).first()

        if not mentor or not get_mentor_scopes(user_id):
            return CustomResponse(
                general_message="Mentor profile not found or not approved."
            ).get_failure_response(status_code=404)

        data = request.data.copy()

        serializer = serializers.MentorProfileSerializer(
            mentor, data=data, partial=True, context={"user_id": user_id}
        )

        if serializer.is_valid():
            general_message = "Mentor profile updated successfully."
            new_url_pending = False

            if 'linkedin' in serializer.validated_data:
                linkedin_url = serializer.validated_data.get('linkedin')

                if linkedin_url:
                    if MentorApplication.objects.filter(
                        user_id=user_id, status=MentorApplication.Status.PENDING,
                        about="[LinkedIn URL Update Request]",
                    ).exists():
                        return CustomResponse(general_message="You already have a pending LinkedIn URL update request.").get_failure_response()

                    now = DateTimeUtils.get_current_utc_time()
                    MentorApplication.objects.create(
                        user_id=user_id,
                        tier=UserMentor.MentorTier.MENTOR,
                        status=MentorApplication.Status.PENDING,
                        source=MentorApplication.SourceType.SELF_APPLIED,
                        about="[LinkedIn URL Update Request]",
                        expertise=linkedin_url,
                        reason="User requested LinkedIn URL update from profile.",
                        hours=mentor.hours,
                        created_by_id=user_id,
                        updated_by_id=user_id,
                        created_at=now,
                        updated_at=now,
                    )
                    general_message = "Profile updated. LinkedIn URL change has been submitted for verification."
                    new_url_pending = True
                else:
                    socials, _ = Socials.objects.get_or_create(user_id=user_id)
                    socials.linkedin = None
                    socials.save(update_fields=['linkedin'])

            serializer.save()

            response_serializer = serializers.MentorProfileSerializer(mentor)
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
        applications = MentorApplication.objects.all()

        status = request.query_params.get("status")
        mentor_tier = request.query_params.get("mentor_tier")

        if status:
            applications = applications.filter(status=status)
        if mentor_tier:
            applications = applications.filter(tier=mentor_tier)

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
        responses={200: serializers.MentorProfileSerializer(many=True)},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        mentor_tier = request.query_params.get("mentor_tier")
        low_rating = request.query_params.get("low_rating", "").lower() == "true"

        mentor_ids = MentorScopeGrant.objects.filter(is_active=True)
        if mentor_tier:
            mentor_ids = mentor_ids.filter(scope_type=mentor_tier)
        mentor_ids = mentor_ids.values_list('mentor_id', flat=True).distinct()

        mentors = UserMentor.objects.filter(id__in=mentor_ids, is_active=True)

        if low_rating:
            from django.db.models import Avg, Count
            from db.mentor import MentorshipSessionUserLink
            low_rated_user_ids = (
                MentorshipSessionUserLink.objects.filter(
                    participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
                    rating__isnull=False,
                )
                .values('user_id')
                .annotate(avg_rating=Avg('rating'), rating_count=Count('id'))
                .filter(avg_rating__lt=3.0, rating_count__gte=5)
                .values_list('user_id', flat=True)
            )
            mentors = mentors.filter(user_id__in=list(low_rated_user_ids))

        paginated_queryset = CommonUtils.get_paginated_queryset(
            mentors, request,
            search_fields=["user__full_name", "user__email"],
            sort_fields={"created_at": "created_at", "user_full_name": "user__full_name"}
        )

        serializer = serializers.MentorProfileSerializer(paginated_queryset.get("queryset"), many=True)
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
        responses={200: serializers.MentorApplicationDetailSerializer},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request, mentor_id):
        mentor = MentorApplication.objects.filter(id=mentor_id).first()
        if not mentor:
            return CustomResponse(
                general_message="Mentor application not found."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.MentorDetailSerializer(mentor)
        return CustomResponse(response=serializer.data).get_success_response()

def _is_company_owner_of_org(actor_id, org):
    """True if `actor_id` owns the verified Company backing `org`."""
    if not org:
        return False
    from db.company import Company
    return Company.objects.filter(
        company_user_id=actor_id,
        status="verified",
        org_id=org.id,
    ).exists()


def _is_company_owner_of_mentor(actor_id, mentor):
    """
    True if `actor_id` owns a verified Company for which `mentor` (a
    UserMentor profile row) holds an active COMPANY_MENTOR grant. Used by
    the scope-grant list/revoke endpoints, which operate on the profile
    rather than a single application.
    """
    from db.company import Company

    org_ids = MentorScopeGrant.objects.filter(
        mentor=mentor, scope_type=MentorScopeGrant.ScopeType.COMPANY_MENTOR, is_active=True,
    ).values_list('scope_id', flat=True)
    if not org_ids:
        return False
    return Company.objects.filter(
        company_user_id=actor_id, status="verified", org_id__in=list(org_ids),
    ).exists()


class MentorVerifyAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description=(
            "Verify or reject a mentor application. Platform admins can "
            "verify any application EXCEPT COMPANY_MENTOR, which is verified "
            "solely by the target company's owner."
        ),
        request=serializers.MentorVerifySerializer,
    )
    def patch(self, request, mentor_id):
        user_id = JWTUtils.fetch_user_id(request)
        application = MentorApplication.objects.select_related('verified_by', 'updated_by', 'org', 'user').filter(id=mentor_id).first()

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
        is_owner = _is_company_owner_of_org(user_id, application.org)

        # Authorization: COMPANY_MENTOR is owner-only — admin has no
        # approval authority over this tier (§4.5). Every other tier is
        # admin-only.
        if application.tier == UserMentor.MentorTier.COMPANY_MENTOR:
            if is_admin and not is_owner:
                return CustomResponse(
                    general_message="Company mentor applications are verified by the company owner only."
                ).get_failure_response(status_code=403)
            can_verify = is_owner
        else:
            can_verify = is_admin

        if not can_verify:
            return CustomResponse(
                general_message="You are not authorized to verify this mentor application."
            ).get_failure_response(status_code=403)

        if application.status in [MentorApplication.Status.APPROVED, MentorApplication.Status.REJECTED]:
            actor = application.verified_by or application.updated_by
            actor_name = "an administrator"
            if actor:
                if _is_company_owner_of_org(actor.id, application.org):
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
        responses={200: serializers.MentorProfileSerializer},
    )
    def get(self, request, mentor_id):
        mentor = UserMentor.objects.filter(id=mentor_id, is_active=True).first()

        if not mentor or not get_mentor_scopes(mentor.user_id):
            return CustomResponse(
                general_message="Mentor profile not found or not approved."
            ).get_failure_response(status_code=404)

        serializer = serializers.MentorProfileSerializer(mentor)
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

        if MentorApplication.objects.filter(user_id=user_id, org=new_company_org, status=MentorApplication.Status.PENDING).exists():
            return CustomResponse(general_message="You already have a pending request for this company.").get_failure_response()

        if MentorScopeGrant.objects.filter(
            mentor__user_id=user_id, scope_type=UserMentor.MentorTier.COMPANY_MENTOR,
            scope_id=str(new_company_org.id), is_active=True,
        ).exists():
            return CustomResponse(general_message="You are already an approved mentor for this company.").get_failure_response()

        existing_mentor_profile = UserMentor.objects.filter(user_id=user_id).first()

        now = DateTimeUtils.get_current_utc_time()
        new_application = MentorApplication.objects.create(
            user_id=user_id,
            org=new_company_org,
            tier=UserMentor.MentorTier.COMPANY_MENTOR,
            status=MentorApplication.Status.PENDING,
            source=MentorApplication.SourceType.SELF_APPLIED,
            about=existing_mentor_profile.about if existing_mentor_profile else None,
            expertise=existing_mentor_profile.expertise if existing_mentor_profile else None,
            hours=existing_mentor_profile.hours if existing_mentor_profile else 0,
            reason=reason,
            nomination_expires_at=now + timedelta(days=NOMINATION_EXPIRY_DAYS),
            created_by_id=user_id,
            updated_by_id=user_id,
            created_at=now,
            updated_at=now,
        )

        serializer = serializers.MentorRegisterSerializer(new_application)
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
                mentor__user_id=user_id, mentor__is_active=True, is_active=True,
            ).values('scope_type', 'scope_id')
        )

        return CustomResponse(response={
            "active_persona": active_persona,
            "active_scope_type": active_scope_type,
            "active_scope_id": active_scope_id,
            "available_scopes": available_scopes,
        }).get_success_response()


class PersonaSwitchAPI(APIView):
    """
    POST persona/switch/ — switch between 'learner' and 'mentor' mode, and
    while in mentor mode select which active scope (IG/campus/company) is
    currently in effect. Writes a SystemActionLog(PERSONA_SWITCH) entry.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Switch active persona (learner/mentor) and, for mentor, the active scope.",
        request=inline_serializer(
            name='PersonaSwitchRequest',
            fields={
                'persona': rest_serializers.ChoiceField(choices=['learner', 'mentor']),
                'scope_type': rest_serializers.CharField(required=False, allow_null=True),
                'scope_id': rest_serializers.CharField(required=False, allow_null=True),
            }
        ),
        responses={200: None},
    )
    def post(self, request):
        from db.user import UserSettings
        from db.mentor import SystemActionLog

        user_id = JWTUtils.fetch_user_id(request)
        persona = request.data.get('persona')
        scope_type = request.data.get('scope_type')
        scope_id = request.data.get('scope_id')

        if persona not in ('learner', 'mentor'):
            return CustomResponse(
                general_message="persona must be 'learner' or 'mentor'."
            ).get_failure_response()

        if persona == 'mentor':
            if not scope_type or not scope_id:
                return CustomResponse(
                    general_message="scope_type and scope_id are required to switch into mentor mode."
                ).get_failure_response()

            has_grant = MentorScopeGrant.objects.filter(
                mentor__user_id=user_id, mentor__is_active=True,
                scope_type=scope_type, scope_id=str(scope_id), is_active=True,
            ).exists()
            if not has_grant:
                return CustomResponse(
                    general_message="You do not hold an active mentor grant for that scope."
                ).get_failure_response(status_code=403)
        else:
            scope_type = None
            scope_id = None

        now = DateTimeUtils.get_current_utc_time()
        settings_row, _ = UserSettings.objects.get_or_create(
            user_id=user_id,
            defaults={"created_by_id": user_id, "updated_by_id": user_id},
        )
        old_data = {
            "active_persona": settings_row.active_persona,
            "active_scope_type": settings_row.active_scope_type,
            "active_scope_id": settings_row.active_scope_id,
        }

        settings_row.active_persona = persona
        settings_row.active_scope_type = scope_type
        settings_row.active_scope_id = scope_id
        settings_row.last_persona_switched_at = now
        settings_row.updated_by_id = user_id
        settings_row.save(update_fields=[
            "active_persona", "active_scope_type", "active_scope_id",
            "last_persona_switched_at", "updated_by_id",
        ])

        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.PERSONA_SWITCH,
            actor_user_id=user_id,
            subject_user_id=user_id,
            entity_name='user_settings',
            entity_id=settings_row.id,
            old_data=old_data,
            new_data={"active_persona": persona, "active_scope_type": scope_type, "active_scope_id": scope_id},
        )

        return CustomResponse(
            general_message="Persona switched successfully.",
            response={
                "active_persona": persona,
                "active_scope_type": scope_type,
                "active_scope_id": scope_id,
            },
        ).get_success_response()


class AdminMentorDeactivateAPI(APIView):
    """
    Admin-only mentor deactivation (addon §6.1) — freezes a mentor's whole
    account (blocks new session/event/job/opportunity creation) without
    touching any individual MentorScopeGrant or deleting history. Distinct
    from revoking a scope grant, which only removes one tier's authority.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Deactivate a mentor's account entirely (e.g. reported misconduct).",
        request=inline_serializer(
            name='MentorDeactivateRequest',
            fields={'reason': rest_serializers.CharField(required=True)}
        ),
        responses={200: None},
    )
    @role_required([RoleType.ADMIN.value])
    def post(self, request, mentor_id):
        admin_id = JWTUtils.fetch_user_id(request)
        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return CustomResponse(general_message="A reason is required to deactivate a mentor.").get_failure_response()

        mentor = UserMentor.objects.filter(id=mentor_id).first()
        if not mentor:
            return CustomResponse(general_message="Mentor not found.").get_failure_response(status_code=404)

        if not mentor.is_active:
            return CustomResponse(general_message="This mentor is already deactivated.").get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        mentor.is_active = False
        mentor.deactivated_by_id = admin_id
        mentor.deactivated_at = now
        mentor.deactivation_reason = reason
        mentor.updated_by_id = admin_id
        mentor.updated_at = now
        mentor.save(update_fields=[
            "is_active", "deactivated_by_id", "deactivated_at",
            "deactivation_reason", "updated_by_id", "updated_at",
        ])

        from db.mentor import SystemActionLog
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.MENTOR_VERIFY,
            actor_user_id=admin_id,
            subject_user_id=mentor.user_id,
            entity_name='user_mentor',
            entity_id=mentor.id,
            old_data={'is_active': True},
            new_data={'is_active': False},
            remarks=reason,
        )

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            actor = User.every.filter(id=admin_id).first()
            NotificationUtils.insert_notification(
                user=mentor.user,
                title="Mentor Account Deactivated",
                description=f"Your mentor account has been deactivated. Reason: {reason}",
                button=None, url=None, created_by=actor,
            )
        except Exception:
            pass

        return CustomResponse(general_message="Mentor deactivated successfully.").get_success_response()


class AdminMentorReactivateAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Reactivate a previously deactivated mentor's account.",
        responses={200: None},
    )
    @role_required([RoleType.ADMIN.value])
    def post(self, request, mentor_id):
        admin_id = JWTUtils.fetch_user_id(request)

        mentor = UserMentor.objects.filter(id=mentor_id).first()
        if not mentor:
            return CustomResponse(general_message="Mentor not found.").get_failure_response(status_code=404)

        if mentor.is_active:
            return CustomResponse(general_message="This mentor is already active.").get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        mentor.is_active = True
        mentor.deactivated_by = None
        mentor.deactivated_at = None
        mentor.deactivation_reason = None
        mentor.updated_by_id = admin_id
        mentor.updated_at = now
        mentor.save(update_fields=[
            "is_active", "deactivated_by", "deactivated_at",
            "deactivation_reason", "updated_by_id", "updated_at",
        ])

        from db.mentor import SystemActionLog
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.MENTOR_VERIFY,
            actor_user_id=admin_id,
            subject_user_id=mentor.user_id,
            entity_name='user_mentor',
            entity_id=mentor.id,
            old_data={'is_active': False},
            new_data={'is_active': True},
        )

        return CustomResponse(general_message="Mentor reactivated successfully.").get_success_response()


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

        qs = MentorScopeGrant.objects.filter(mentor=mentor, is_active=True)
        if mentor_tier:
            qs = qs.filter(scope_type=mentor_tier)

        grants = list(qs)
        if not grants:
            return CustomResponse(
                general_message="No active mentor grants found to revoke."
            ).get_failure_response(status_code=404)

        now = DateTimeUtils.get_current_utc_time()

        with transaction.atomic():
            # Deactivate the matching grants. NOTE: revoking mentor authority
            # must never touch UserOrganizationLink — that's the user's
            # employment/identity record, not a permission.
            grant_ids = [g.id for g in grants]
            MentorScopeGrant.objects.filter(id__in=grant_ids).update(
                is_active=False, revoked_by_id=admin_id, revoked_at=now,
            )

            # Deactivate IG links for any revoked IG_MENTOR scopes.
            if any(g.scope_type == MentorScopeGrant.ScopeType.IG_MENTOR for g in grants):
                revoked_ig_ids = [
                    g.scope_id for g in grants
                    if g.scope_type == MentorScopeGrant.ScopeType.IG_MENTOR and g.scope_id
                ]
                if revoked_ig_ids:
                    UserIgLink.objects.filter(
                        user=user,
                        ig_id__in=revoked_ig_ids,
                        assignment_type=UserIgLink.AssignmentType.MENTOR,
                    ).update(is_active=False)

            # Strip the Mentor role only if no active grants remain at all.
            remaining_active = MentorScopeGrant.objects.filter(mentor=mentor, is_active=True).exists()
            if not remaining_active:
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
        if not is_admin and not _is_company_owner_of_mentor(actor_id, mentor):
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
        if not is_admin and not _is_company_owner_of_mentor(actor_id, mentor):
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
