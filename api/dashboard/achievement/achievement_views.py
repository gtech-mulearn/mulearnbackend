from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from django.http import FileResponse
from io import BytesIO
import openpyxl
from db.achievement import Achievement, UserAchievementsLog
from db.user import User
from django.db.models import Q
from utils.types import RoleType
from utils.utils import CommonUtils
from . import achievement_serializer
from db.achievement import Achievement, UserAchievementsLog
from utils.response import CustomResponse
from utils.permission import JWTUtils
from db.user import User
from db.task import Level
import uuid
from django.utils.timezone import now
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from utils.utils import ImportCSV


class AchievementListAPIView(APIView):
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        user = User.objects.filter(id=user_id).first()

        if not user:
            return CustomResponse(
                general_message="User Not Exists"
            ).get_failure_response()

        achievements = Achievement.objects.all()
        achievements_serializer = achievement_serializer.AchievementSerializer(
            achievements, many=True
        )

        return CustomResponse(
            response=achievements_serializer.data
        ).get_success_response()


class AchievementCreateAPIView(APIView):
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(
                general_message="User Not Exists"
            ).get_failure_response()

        data = request.data
        required_fields = ["name", "description", "icon", "tags", "type", "has_vc"]

        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return CustomResponse(
                general_message=f"Missing required fields: {', '.join(missing_fields)}"
            ).get_failure_response()

        if Achievement.objects.filter(name=data["name"]).exists():
            return CustomResponse(
                general_message="Name already exists"
            ).get_failure_response()

        level = None
        if "level_id" in data and data["level_id"]:
            try:
                level = Level.objects.get(id=data["level_id"])
            except Level.DoesNotExist:
                return CustomResponse(
                    general_message="Invalid level_id"
                ).get_failure_response()

        achievement = Achievement.objects.create(
            id=str(uuid.uuid4()),
            name=data["name"],
            description=data["description"],
            icon=data["icon"],
            tags=data["tags"],
            type=data["type"],
            level_id=level,
            has_vc=data["has_vc"],
            template_id=data.get("template_id"),
            created_by=user,
            updated_by=user,
            created_at=now(),
            updated_at=now(),
        )

        return CustomResponse(
            general_message=f"Achievement '{achievement.name}' created successfully!"
        ).get_success_response()


class AchievementUpdateAPIView(APIView):
    def put(self, request, achievement_id=None):
        user_id = JWTUtils.fetch_user_id(request)

        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(
                general_message="User Not Exists"
            ).get_failure_response()

        if not achievement_id:
            return CustomResponse(
                general_message="Achievement ID is required"
            ).get_failure_response()

        try:
            achievement = Achievement.objects.get(id=achievement_id)
        except Achievement.DoesNotExist:
            return CustomResponse(
                general_message="Achievement not found"
            ).get_failure_response()

        data = request.data.copy()
        data["updated_by"] = user_id

        if "level_id" in data:
            if data["level_id"]:
                try:
                    level = Level.objects.get(id=data["level_id"])
                    data["level_id"] = level.id
                except Level.DoesNotExist:
                    return CustomResponse(
                        general_message="Invalid level_id"
                    ).get_failure_response()
            else:
                data["level_id"] = None

        serializer = achievement_serializer.AchievementSerializer(
            achievement, data=data, partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Achievement updated successfully"
            ).get_success_response()

        return CustomResponse(
            general_message="Invalid Data", response=serializer.errors
        ).get_failure_response()


class AchievementDeleteAPIView(APIView):
    def delete(self, request, achievement_id):
        user_id = JWTUtils.fetch_user_id(request)

        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(
                general_message="User Not Exists"
            ).get_failure_response()

        try:
            achievement = Achievement.objects.get(id=achievement_id)
        except Achievement.DoesNotExist:
            return CustomResponse(
                general_message="Achievement not found"
            ).get_failure_response()

        achievement.delete()
        return CustomResponse(
            general_message="Achievement deleted successfully"
        ).get_success_response()


class UserAchievementsListAPIView(APIView):
    def get(self, request, muid):
        try:
            user = get_object_or_404(User, muid=muid)

            user_achievements = (
                UserAchievementsLog.objects.filter(user_id=user.id)
                .select_related("achievement_id")
                .only(
                    "id",
                    "user_id",
                    "achievement_id",
                    "is_issued",
                    "vc_url",
                    "achievement_id__name",
                    "achievement_id__description",
                )
            )

            # if not user_achievements.exists():
            #     return CustomResponse(
            #         general_message="No achievements found for this user"
            #     ).get_failure_response()

            serializer = achievement_serializer.UserAchievementsSerializer(
                user_achievements, many=True
            )
            return CustomResponse(response=serializer.data).get_success_response()

        except ValidationError:
            return CustomResponse(
                general_message="Invalid format for muid"
            ).get_failure_response()

        except Exception as e:
            return CustomResponse(
                general_message=f"An unexpected error occurred: {str(e)}"
            ).get_failure_response()


class UserAchievementsIssueAPIView(APIView):
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        achievement_id = request.data.get("achievement_id")
        vc_url = request.data.get("vc_url")

        if not achievement_id:
            return CustomResponse(
                general_message="Achievement ID is required"
            ).get_failure_response()

        if not vc_url:
            return CustomResponse(
                general_message="VC URL is required"
            ).get_failure_response()

        if not User.objects.filter(id=user_id).exists():
            return CustomResponse(
                general_message="User Not Exists"
            ).get_failure_response()

        try:
            user_achievement = UserAchievementsLog.objects.get(
                user_id=user_id, achievement_id=achievement_id
            )
        except UserAchievementsLog.DoesNotExist:
            return CustomResponse(
                general_message="Achievement record not found"
            ).get_failure_response()

        if user_achievement.is_issued:
            return CustomResponse(
                general_message="This achievement has already been issued"
            ).get_failure_response()

        UserAchievementsLog.objects.filter(
            user_id=user_id, achievement_id=achievement_id
        ).update(is_issued=True, vc_url=vc_url)

        return CustomResponse(
            general_message="Achievement issued successfully"
        ).get_success_response()


class AchievementIssueBulkAPIView(APIView):
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(
                general_message="User Not Exists"
            ).get_failure_response()

        achievement_id = request.data.get("achievement_id")
        if not achievement_id:
            return CustomResponse(
                general_message="Achievement ID is required"
            ).get_failure_response()

        try:
            achievement = Achievement.objects.get(id=achievement_id)
        except Achievement.DoesNotExist:
            return CustomResponse(
                general_message="Achievement not found"
            ).get_failure_response()

        try:
            file_obj = request.FILES["file"]
        except KeyError:
            return CustomResponse(
                general_message="File not found"
            ).get_failure_response()

        excel_data = ImportCSV()
        try:
            excel_data = excel_data.read_excel_file(file_obj)
        except Exception as e:
            return CustomResponse(
                general_message="Error reading Excel file", response=str(e)
            ).get_failure_response()

        if not excel_data:
            return CustomResponse(
                general_message="Empty Excel file"
            ).get_failure_response()

        # Assuming the first row is header and contains 'muid'
        # ImportCSV.read_excel_file returns a list of dictionaries where keys are headers
        
        # Validate headers
        header_keys = excel_data[0].keys()
        if "muid" not in [key.lower() for key in header_keys if key]:
             return CustomResponse(
                general_message="Excel file must contain 'muid' column"
            ).get_failure_response()

        created_count = 0
        updated_count = 0
        failed_muids = []

        for row in excel_data:
            # Find the key that corresponds to 'muid' (case-insensitive)
            muid_key = next((k for k in row.keys() if k and k.lower() == 'muid'), None)
            muid = row.get(muid_key)

            if not muid:
                continue

            muid = str(muid).strip()
            
            try:
                user_to_issue = User.objects.get(muid=muid)
                
                # Check if already exists
                user_achievement, created = UserAchievementsLog.objects.get_or_create(
                    user_id=user_to_issue,
                    achievement_id=achievement,
                    defaults={
                        "id": str(uuid.uuid4()),
                        "created_by": user,
                        "updated_by": user,
                        "is_issued": False, # Setting to False initially as per discussion logic (claimable)
                        "vc_url": "" # No VC URL in bulk issuance
                    }
                )

                if created:
                    created_count += 1
                else:
                    # Optional: Update metadata if needed, for now just counting
                    updated_count += 1
            
            except User.DoesNotExist:
                failed_muids.append(f"{muid}: User not found")
            except Exception as e:
                 failed_muids.append(f"{muid}: {str(e)}")

        return CustomResponse(
            general_message="Bulk issuance processed",
            response={
                "created": created_count,
                "updated": updated_count,
                "failed_count": len(failed_muids),
                "failed_muids": failed_muids
            }
        ).get_success_response()


class AchievementBulkImportTemplateAPIView(APIView):
    def get(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Bulk Import Template"
        ws.append(["muid"])
        
        # Add sample data or just leave it with header
        # ws.append(["user@mulearn"]) 

        with BytesIO() as f:
            wb.save(f)
            f.seek(0)
            data = f.read()

        response = FileResponse(
            BytesIO(data),
            as_attachment=True,
            filename="achievement_bulk_import_template.xlsx"
        )
        return response


class AchievementLogListAPIView(APIView):
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        # You might want to restrict this to admins
        # if not User.objects.filter(id=user_id, user_role_link_user__role__title=RoleType.ADMIN.value).exists():
        #     return CustomResponse(general_message="You do not have permission").get_failure_response()

        queryset = UserAchievementsLog.objects.select_related(
            'user_id', 'achievement_id', 'created_by'
        ).all().order_by('-created_at')

        # Search functionality
        search_query = request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(user_id__muid__icontains=search_query) |
                Q(user_id__full_name__icontains=search_query) |
                Q(achievement_id__name__icontains=search_query)
            )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            queryset, request, ['user_id__full_name', 'created_at']
        )

        data = []
        for log in paginated_queryset.get('queryset'):
            data.append({
                "id": log.id,
                "muid": log.user_id.muid,
                "user_name": log.user_id.full_name,
                "achievement": log.achievement_id.name,
                "issued_by": log.created_by.full_name,
                "issued_on": log.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        return CustomResponse(
            response={
                "data": data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()
