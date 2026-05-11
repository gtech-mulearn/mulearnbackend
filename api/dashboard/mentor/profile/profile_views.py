from rest_framework.views import APIView

from db.user import User, UserMentor
from utils.permission import CustomizePermission, JWTUtils
from utils.mentor_permissions import IsIGMentor
from utils.response import CustomResponse
from django.utils import timezone


class MentorProfileView(APIView):
    """
    GET  /api/v1/dashboard/mentor/profile/  — fetch own mentor profile
    PATCH /api/v1/dashboard/mentor/profile/ — update about/reason/expertise
    """
    permission_classes = [CustomizePermission, IsIGMentor]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        profile = UserMentor.objects.filter(user_id=user_id).first()

        if not profile:
            return CustomResponse(
                general_message="Mentor profile not found."
            ).get_failure_response()

        return CustomResponse(
            general_message="Mentor profile fetched.",
            response={
                "id": profile.id,
                "about": profile.about,
                "reason": profile.reason,
                "expertise": profile.expertise,
                "volunteer_hours": profile.hours,
                "mentor_tier": profile.mentor_tier,
                "is_verified": profile.is_verified,
                "verified_at": profile.verified_at.isoformat() if profile.verified_at else None,
                "verification_note": profile.verification_note,
            }
        ).get_success_response()

    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(general_message="User not found.").get_failure_response()

        profile = UserMentor.objects.filter(user=user).first()
        if not profile:
            return CustomResponse(general_message="Mentor profile not found.").get_failure_response()

        allowed_fields = {'about', 'reason', 'expertise'}
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        if not update_data:
            return CustomResponse(
                general_message="No valid fields provided for update."
            ).get_failure_response()

        for field, value in update_data.items():
            setattr(profile, field, value)

        profile.updated_by = user
        profile.updated_at = timezone.now()
        profile.save(update_fields=list(update_data.keys()) + ['updated_by', 'updated_at'])

        return CustomResponse(
            general_message="Mentor profile updated.",
            response={
                "id": profile.id,
                "about": profile.about,
                "reason": profile.reason,
                "expertise": profile.expertise,
                "volunteer_hours": profile.hours,
                "mentor_tier": profile.mentor_tier,
                "is_verified": profile.is_verified,
            }
        ).get_success_response()
