import json
import os
import uuid
from io import BytesIO

import openpyxl
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import FileResponse
from django.utils.timezone import now
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from db.achievement import (
    Achievement,
    AchievementAuditLog,
    AchievementRule,
    UserAchievementsLog,
)
from db.task import Level
from db.user import User
from utils.permission import JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils
from . import achievement_serializer


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
    parser_classes = [MultiPartParser, FormParser]

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
        # Icon can be either a file upload or a text URL
        icon_file = request.FILES.get("icon")
        icon_url = data.get("icon", "") if not icon_file else ""
        
        required_fields = ["name", "description", "tags", "type", "has_vc"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return CustomResponse(
                general_message=f"Missing required fields: {', '.join(missing_fields)}"
            ).get_failure_response()

        # Parse has_vc from string to boolean (FormData sends strings)
        has_vc_value = data.get("has_vc")
        if isinstance(has_vc_value, str):
            has_vc_value = has_vc_value.lower() in ("true", "1", "yes")
        
        tags_value = data.get("tags", [])
        if isinstance(tags_value, str):
            try:
                tags_value = json.loads(tags_value)
            except json.JSONDecodeError:
                tags_value = []

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

        # Handle icon file upload
        icon_path = icon_url  # Default to URL if provided
        if icon_file:
            # Validate file type
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']
            file_ext = icon_file.name.split('.')[-1].lower()
            if file_ext not in allowed_extensions:
                return CustomResponse(
                    general_message=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
                ).get_failure_response()
            
            # Validate file size (max 5MB)
            if icon_file.size > 5 * 1024 * 1024:
                return CustomResponse(
                    general_message="File size exceeds 5MB limit"
                ).get_failure_response()
            
            # Create directory if it doesn't exist
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'achievements', 'icons')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}.{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Save file
            with open(file_path, 'wb+') as destination:
                for chunk in icon_file.chunks():
                    destination.write(chunk)
            
            # Store relative path for database
            icon_path = f"achievements/icons/{unique_filename}"

        achievement = Achievement.objects.create(
            id=str(uuid.uuid4()),
            name=data["name"],
            description=data["description"],
            icon=icon_path,
            tags=tags_value,
            type=data["type"],
            level_id=level,
            has_vc=has_vc_value,
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
    parser_classes = [MultiPartParser, FormParser]

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

        # Convert QueryDict to regular dict to properly handle list/boolean assignments
        data = dict(request.data)
        # QueryDict wraps values in lists, so unwrap single values
        for key in data:
            if isinstance(data[key], list) and len(data[key]) == 1:
                data[key] = data[key][0]
        data["updated_by"] = user_id

        # Handle icon file upload
        icon_file = request.FILES.get("icon")
        if icon_file:
            # Validate file type
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']
            file_ext = icon_file.name.split('.')[-1].lower()
            if file_ext not in allowed_extensions:
                return CustomResponse(
                    general_message=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
                ).get_failure_response()
            
            # Validate file size (max 5MB)
            if icon_file.size > 5 * 1024 * 1024:
                return CustomResponse(
                    general_message="File size exceeds 5MB limit"
                ).get_failure_response()
            
            # Create directory if it doesn't exist
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'achievements', 'icons')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            unique_filename = f"{uuid.uuid4()}.{file_ext}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Save file
            with open(file_path, 'wb+') as destination:
                for chunk in icon_file.chunks():
                    destination.write(chunk)
            
            # Store relative path for database
            data["icon"] = f"achievements/icons/{unique_filename}"
        elif "icon" not in data or not data["icon"]:
            # Keep existing icon if no new file or URL provided
            data["icon"] = achievement.icon

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

        # Parse has_vc from string to boolean (FormData sends strings)
        if "has_vc" in data:
            has_vc_value = data.get("has_vc")
            if isinstance(has_vc_value, str):
                data["has_vc"] = has_vc_value.lower() in ("true", "1", "yes")
        
        # Parse tags from JSON string to list (FormData sends strings)
        if "tags" in data:
            tags_value = data.get("tags", [])
            if isinstance(tags_value, str):
                try:
                    data["tags"] = json.loads(tags_value)
                except json.JSONDecodeError:
                    data["tags"] = []

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

        if not User.objects.filter(id=user_id).exists():
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


# ============================================================================
# NEW ACHIEVEMENT SYSTEM VIEWS
# ============================================================================


class EligibleAchievementsAPIView(APIView):
    """Get achievements the current user is eligible to claim"""

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        from api.dashboard.achievement.rule_engine import RuleEvaluator

        evaluator = RuleEvaluator(user_id)
        eligible = evaluator.get_eligible_achievements()

        response_data = [
            {
                "achievement_id": result.achievement_id,
                "achievement_name": result.achievement_name,
                "eligible": result.eligible,
                "reason": result.reason,
                "progress": result.progress,
            }
            for result in eligible
        ]

        return CustomResponse(response=response_data).get_success_response()


class ClaimAchievementAPIView(APIView):
    """Claim an achievement (user action)"""

    def post(self, request, achievement_id):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        from mu_celery.achievement_tasks import claim_achievement

        result = claim_achievement(user_id, achievement_id)

        if result["success"]:
            return CustomResponse(
                general_message=result["message"],
                response={
                    "achievement_name": result.get("achievement_name"),
                    "vc_pending": result.get("vc_pending", False),
                },
            ).get_success_response()
        else:
            return CustomResponse(
                general_message=result["message"],
                response={"progress": result.get("progress")},
            ).get_failure_response()


class UserProgressAPIView(APIView):
    """Get progress towards all achievements"""

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        from api.dashboard.achievement.rule_engine import RuleEvaluator

        evaluator = RuleEvaluator(user_id)
        all_progress = evaluator.get_all_progress()

        response_data = [
            {
                "achievement_id": result.achievement_id,
                "achievement_name": result.achievement_name,
                "eligible": result.eligible,
                "reason": result.reason,
                "progress": result.progress,
            }
            for result in all_progress
        ]

        return CustomResponse(response=response_data).get_success_response()


class AchievementRuleListAPIView(APIView):
    """List all achievement rules (admin)"""

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        rules = AchievementRule.objects.all().select_related("achievement")
        data = [
            {
                "id": str(rule.id),
                "achievement_id": str(rule.achievement_id),
                "achievement_name": rule.achievement.name,
                "version": rule.version,
                "rule_type": rule.rule_type,
                "conditions": rule.conditions,
                "is_active": rule.is_active,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
            }
            for rule in rules
        ]

        return CustomResponse(response=data).get_success_response()


class AchievementRuleCreateAPIView(APIView):
    """Create a new achievement rule (admin)"""

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        data = request.data
        required_fields = ["achievement_id", "rule_type", "conditions"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return CustomResponse(
                general_message=f"Missing required fields: {', '.join(missing_fields)}"
            ).get_failure_response()

        # Get next version number
        existing_versions = AchievementRule.objects.filter(
            achievement_id=data["achievement_id"]
        ).values_list("version", flat=True)
        next_version = max(existing_versions) + 1 if existing_versions else 1

        # Deactivate existing rules for this achievement
        AchievementRule.objects.filter(
            achievement_id=data["achievement_id"], is_active=True
        ).update(is_active=False)

        rule = AchievementRule.objects.create(
            id=str(uuid.uuid4()),
            achievement_id=data["achievement_id"],
            version=next_version,
            rule_type=data["rule_type"],
            conditions=data["conditions"],
            is_active=True,
            created_by_id=user_id,
            created_at=now(),
            updated_at=now(),
        )

        return CustomResponse(
            general_message=f"Rule v{next_version} created successfully",
            response={"rule_id": str(rule.id), "version": next_version},
        ).get_success_response()


class AchievementRuleDetailAPIView(APIView):
    """Get details of a specific rule (admin)"""

    def get(self, request, rule_id):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
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

                if muid.lower() == 'muid':
                    continue
                
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
        except Exception as e:
            import traceback
            return CustomResponse(
                general_message=f"Server error: {str(e)}",
                response={"traceback": traceback.format_exc()}
            ).get_failure_response(status_code=500)


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

        try:
            target_user = User.objects.get(muid=muid)
        except User.DoesNotExist:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()

        audit_logs = (
            AchievementAuditLog.objects.filter(user_id=target_user.id)
            .select_related("achievement")
            .order_by("-created_at")[:100]
        )

        data = [
            {
                "id": str(log.id),
                "achievement_id": str(log.achievement_id),
                "achievement_name": log.achievement.name,
                "action": log.action,
                "rule_version": log.rule_version,
                "metadata": log.metadata,
                "performed_by": str(log.performed_by_id) if log.performed_by_id else None,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in audit_logs
        ]

        return CustomResponse(response=data).get_success_response()



class AchievementIssueBulkAPIView(APIView):
    from rest_framework.parsers import MultiPartParser, FormParser
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            return CustomResponse(
                general_message="No file uploaded"
            ).get_failure_response()

        try:
            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active
            
            headers = [cell.value for cell in sheet[1]]
            required_headers = ['muid', 'achievement_id']
            
            if not all(h in headers for h in required_headers):
                return CustomResponse(
                    general_message=f"Missing required headers. Required: {required_headers}"
                ).get_failure_response()
            
            muid_idx = headers.index('muid')
            ach_idx = headers.index('achievement_id')
            
            success_count = 0
            failed_rows = []
            
            from mu_celery.achievement_tasks import manual_issue_achievement

            for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                muid = row[muid_idx]
                achievement_id = row[ach_idx]
                
                if not muid or not achievement_id:
                    continue
                     
                try:
                    user = User.objects.filter(muid=muid).first()
                    if not user:
                        failed_rows.append({"row": i, "muid": muid, "reason": "User not found"})
                        continue

                    result = manual_issue_achievement(
                        user_id=str(user.id),
                        achievement_id=str(achievement_id),
                        performed_by=user_id
                    )
                    
                    if result['success']:
                        success_count += 1
                    else:
                        failed_rows.append({"row": i, "muid": muid, "reason": result['message']})
                        
                except Exception as e:
                    failed_rows.append({"row": i, "muid": muid, "reason": str(e)})

            return CustomResponse(
                response={
                    "success_count": success_count,
                    "failed_count": len(failed_rows),
                    "failed_rows": failed_rows
                },
                general_message="Bulk issue processing completed"
            ).get_success_response()

        except Exception as e:
            return CustomResponse(
                general_message=f"Error processing file: {str(e)}"
            ).get_failure_response()


class AchievementBulkImportTemplateAPIView(APIView):
    def get(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['muid', 'achievement_id'])
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = FileResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=achievement_bulk_import_template.xlsx'
        return response


class AchievementLogListAPIView(APIView):
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()
            
        logs = UserAchievementsLog.objects.select_related('user', 'achievement_id').order_by('-created_at')
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            logs, 
            request, 
            search_fields=['user__muid', 'user__first_name', 'achievement_id__name'],
            sort_fields={'created_at': 'created_at'}
        )
        
        data = []
        for log in paginated_queryset.get('queryset'):
            data.append({
                "id": str(log.id),
                "muid": log.user.muid,
                "user_name": log.user.full_name,
                "achievement_name": log.achievement_id.name,
                "is_issued": log.is_issued,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "issued_by": log.updated_by.full_name if log.updated_by else None
            })
             
        return CustomResponse().paginated_response(
            data=data,
            pagination=paginated_queryset.get('pagination')
        )

