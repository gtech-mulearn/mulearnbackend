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
    from rest_framework.parsers import MultiPartParser, FormParser
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
        
        # Parse tags from JSON string to list (FormData sends strings)
        tags_value = data.get("tags", [])
        if isinstance(tags_value, str):
            import json
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
            import os
            from django.conf import settings
            
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
    from rest_framework.parsers import MultiPartParser, FormParser
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
            import os
            from django.conf import settings
            
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
                import json
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
    """
    Bulk issue achievements for multiple users using an uploaded file.

    This endpoint allows an authorized admin or super admin to mark a given
    achievement as issued for multiple users in a single request. The client
    must upload a tabular file (for example, a CSV or Excel spreadsheet) that
    is compatible with the :class:`ImportCSV` utility. Each row in the file
    should represent one user for whom the specified achievement should be
    issued.

    Authentication/Authorization
    ----------------------------
    - The request must include a valid JWT token; the user ID is extracted
      via :func:`JWTUtils.fetch_user_id`.
    - Only users with roles corresponding to ``RoleType.ADMIN`` or
      ``RoleType.SUPER_ADMIN`` are allowed to perform this operation.

    Request
    -------
    Method: ``POST``

    Body (form-data or multipart/form-data):
      - ``achievement_id`` (str or int, required):
          The ID of the :class:`Achievement` to be issued to users listed in
          the uploaded file.

    Files:
      - ``file`` (required):
          A tabular data file supported by :class:`ImportCSV` (for example,
          CSV or Excel). Each row must contain the user-identifying data and
          any additional fields required by ``ImportCSV`` to locate the user
          and mark the achievement as issued (for example, a user ID or email,
          and optionally an associated VC URL or related metadata).

    Behavior
    --------
    - Validates that the caller is authenticated and has sufficient privileges.
    - Validates that the target achievement exists.
    - Reads and parses the uploaded file via :class:`ImportCSV`.
    - For each valid row, updates or creates the corresponding
      :class:`UserAchievementsLog` entry to mark the achievement as issued,
      following whatever rules are implemented in ``ImportCSV`` and the
      underlying business logic.

    Responses
    ---------
    On success:
      - Returns a :class:`CustomResponse` success payload, typically with a
        general success message indicating that the bulk issue operation
        completed. The precise structure follows the project's standard
        response format used by ``CustomResponse.get_success_response()``.

    On failure:
      - Returns a :class:`CustomResponse` failure payload with an explanatory
        ``general_message``. Examples include:
          * ``"Invalid or missing token"`` if authentication fails.
          * ``"User Not Exists"`` if the requesting user cannot be found.
          * ``"You do not have permission to perform this action"`` if the
            user lacks the required role.
          * ``"Achievement ID is required"`` if the ID is missing.
          * ``"Achievement not found"`` if the specified achievement does not
            exist.
          * ``"File not found"`` if the upload is missing.
    """
    from rest_framework.parsers import MultiPartParser, FormParser
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        try:
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

            if not User.objects.filter(id=user_id, user_role_link_user__role__title=RoleType.ADMIN.value).exists():
                return CustomResponse(
                    general_message="You do not have permission to perform this action"
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

            if len(excel_data) <= 1:
                return CustomResponse(
                    general_message="Excel file contains no data rows"
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

            # Bulk fetch users
            # Pre-process rows to find muids
            processed_rows = []
            
            target_muids = set()
            for row in excel_data:
                 # Find the key that corresponds to 'muid' (case-insensitive)
                muid_key = next((k for k in row.keys() if k and k.lower() == 'muid'), None)
                val = row.get(muid_key)
                if val:
                    muid_str = str(val).strip()
                    if muid_str.lower() != 'muid':
                        target_muids.add(muid_str)
                        processed_rows.append(muid_str)
            
            users_map = {user.muid: user for user in User.objects.filter(muid__in=target_muids)}

            for muid in processed_rows:
                if muid not in users_map:
                    failed_muids.append(f"{muid}: User not found")
                    continue

                user_to_issue = users_map[muid]

                try:
                    # Check if already exists
                    user_achievement, created = UserAchievementsLog.objects.get_or_create(
                        user_id=user_to_issue,
                        achievement_id=achievement,
                        defaults={
                            "id": str(uuid.uuid4()),
                            "created_by": user,
                            "updated_by": user,
                            "is_issued": False, # Setting to False to allow users to claim the achievement later
                            "vc_url": "" # No VC URL in bulk issuance
                        }
                    )

                    if created:
                        created_count += 1
                    else:
                        # Update metadata for existing achievement record
                        user_achievement.updated_by = user
                        user_achievement.save(update_fields=["updated_by"])
                        updated_count += 1
                
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
    """
    Provides an authenticated endpoint to download an Excel template for
    bulk importing user achievement issuances.

    On a successful request with a valid JWT, this view returns a
    `FileResponse` containing a single-sheet `.xlsx` workbook titled
    "Bulk Import Template" with a header row for `muid`. Clients can
    populate this template and use it with the bulk import endpoint.

    If the request does not include a valid token, a failure response
    with an appropriate error message is returned instead of a file.
    """
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not user_id:
            return CustomResponse(
                general_message="Invalid or missing token"
            ).get_failure_response()

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
            issued_by = log.created_by.full_name if log.created_by else None
            data.append({
                "id": log.id,
                "muid": log.user_id.muid,
                "user_name": log.user_id.full_name,
                "achievement": log.achievement_id.name,
                "issued_by": issued_by,
                "issued_on": log.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        return CustomResponse(
            response={
                "data": data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()
