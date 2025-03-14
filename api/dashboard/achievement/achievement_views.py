from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from . import achievement_serializer
from db.achievement import Achievement, UserAchievements
from utils.response import CustomResponse
from utils.permission import JWTUtils
from db.user import User
import uuid
from django.utils.timezone import now
from django.core.exceptions import ObjectDoesNotExist, ValidationError
class AchievementListAPIView(APIView):
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not user_id:
            return CustomResponse(general_message="Invalid or missing token").get_failure_response()

        user = User.objects.filter(id=user_id).first()

        if not user:
            return CustomResponse(general_message="User Not Exists").get_failure_response()

        achievements = Achievement.objects.all()
        achievements_serializer = achievement_serializer.AchievementSerializer(achievements, many=True)

        return CustomResponse(response=achievements_serializer.data).get_success_response()

class AchievementCreateAPIView(APIView):
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not user_id:
            return CustomResponse(general_message="Invalid or missing token").get_failure_response()

        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(general_message="User Not Exists").get_failure_response()


        data = request.data
        required_fields = ["title", "description", "icon", "tags", "type", "level_based", "has_vc"]


        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return CustomResponse(
                general_message=f"Missing required fields: {', '.join(missing_fields)}"
            ).get_failure_response()


        if Achievement.objects.filter(title=data["title"]).exists():
            return CustomResponse(general_message="Title already exists").get_failure_response()


        achievement = Achievement.objects.create(
            id=str(uuid.uuid4()),
            title=data["title"],
            description=data["description"],
            icon=data["icon"],
            tags=data["tags"],
            type=data["type"],
            level_based=data["level_based"],
            has_vc=data["has_vc"],
            created_by=user,
            updated_by=user,
            created_at=now(),
            updated_at=now(),
        )

        # Serialize and return success response
        serializer = achievement_serializer.AchievementSerializer(achievement)
        return CustomResponse(response=serializer.data).get_success_response()

class AchievementUpdateAPIView(APIView):
    def put(self, request, achievement_id=None):
        user_id = JWTUtils.fetch_user_id(request)

        if not user_id:
            return CustomResponse(general_message="Invalid or missing token").get_failure_response()

        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(general_message="User Not Exists").get_failure_response()

        if not achievement_id:
            return CustomResponse(general_message="Achievement ID is required").get_failure_response()

        try:
            achievement = Achievement.objects.get(id=achievement_id)
        except Achievement.DoesNotExist:
            return CustomResponse(general_message="Achievement not found").get_failure_response()

        data = request.data.copy()
        data["updated_by"] = user_id

        serializer = achievement_serializer.AchievementSerializer(achievement, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data, general_message="Achievement updated successfully").get_success_response()
        return CustomResponse(general_message="Invalid Data", response=serializer.errors).get_failure_response()


class AchievementDeleteAPIView(APIView):
    def delete(self, request, achievement_id):
        user_id = JWTUtils.fetch_user_id(request)

        if not user_id:
            return CustomResponse(general_message="Invalid or missing token").get_failure_response()

        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(general_message="User Not Exists").get_failure_response()

        try:
            achievement = Achievement.objects.get(id=achievement_id)
        except Achievement.DoesNotExist:
            return CustomResponse(general_message="Achievement not found").get_failure_response()

        achievement.delete()
        return CustomResponse(general_message="Achievement deleted successfully").get_success_response()

class UserAchievementsListAPIView(APIView):
    def get(self, request, muid):
        try:
            user = get_object_or_404(User, muid=muid)

            user_achievements = (
                UserAchievements.objects
                .filter(user_id=user.id)
                .select_related('achievement_id')
                .only('id', 'user_id', 'achievement_id', 'is_issued', 'vc_url', 'achievement_id__name', 'achievement_id__description')
            )

            # If no achievements found
            if not user_achievements.exists():
                return CustomResponse(general_message="No achievements found for this user").get_failure_response()

            # Serialize and return response
            serializer = achievement_serializer.UserAchievementsSerializer(user_achievements, many=True)
            return CustomResponse(response=serializer.data).get_success_response()

        except ValidationError:
            return CustomResponse(general_message="Invalid format for muid").get_failure_response()

        except Exception as e:
            return CustomResponse(general_message=f"An unexpected error occurred: {str(e)}").get_failure_response()


class UserAchievementsIssueAPIView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return CustomResponse(general_message="Invalid or missing token").get_failure_response()

        achievement_id = request.data.get("achievement_id")
        vc_url = request.data.get("vc_url")

        if not achievement_id:
            return CustomResponse(general_message="Achievement ID is required").get_failure_response()

        if not vc_url:
            return CustomResponse(general_message="VC URL is required").get_failure_response()

        if not User.objects.filter(id=user_id).exists():
            return CustomResponse(general_message="User Not Exists").get_failure_response()

        try:
            user_achievement = UserAchievements.objects.get(user_id=user_id, achievement_id=achievement_id)
        except UserAchievements.DoesNotExist:
            return CustomResponse(general_message="Achievement record not found").get_failure_response()

        if user_achievement.is_issued:
            return CustomResponse(general_message="This achievement has already been issued").get_failure_response()

        UserAchievements.objects.filter(user_id=user_id, achievement_id=achievement_id).update(is_issued=True, vc_url=vc_url)

        return CustomResponse(general_message="Achievement issued successfully").get_success_response()















