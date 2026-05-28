import uuid

from rest_framework.views import APIView

from db.organization import Organization
from db.task import Channel, InterestGroup, Level, TaskList, TaskType
from db.skill import Skill, TaskSkillLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import Events, RoleType
from utils.utils import CommonUtils, DateTimeUtils, ImportCSV
from .dash_task_serializer import (
    TaskImportSerializer,
    TaskListPublicSerializer,
    TaskListSerializer,
    TaskModifySerializer,
    TaskTypeCreateUpdateSerializer,
    TasktypeSerializer,
)

from openpyxl import load_workbook
from tempfile import NamedTemporaryFile
from io import BytesIO
from django.http import FileResponse
from drf_spectacular.utils import extend_schema
from utils.schema_utils import CustomResponseSerializer


class TaskPublicListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Task'],
        description="Retrieve Task Public List.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        task_queryset = TaskList.objects.select_related(
            "channel", "type", "level", "ig", "org"
        ).all()

        ig_id = request.query_params.get("ig_id")
        if ig_id:
            task_queryset = task_queryset.filter(ig_id=ig_id)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            task_queryset,
            request,
            search_fields=[
                "hashtag",
                "title",
                "description",
                "karma",
                "channel__name",
                "type__title",
                "active",
                "variable_karma",
                "usage_count",
                "level__name",
                "org__title",
                "ig__name",
                "event",
            ],
            sort_fields={
                "hashtag": "hashtag",
                "title": "title",
                "description": "description",
                "karma": "karma",
                "channels": "channel__name",
                "type": "type__title",
                "active": "active",
                "variable_karma": "variable_karma",
                "usage_count": "usage_count",
                "level": "level__name",
                "org": "org__title",
                "ig": "ig__name",
                "event": "event",
                "updated_at": "updated_at",
                "created_at": "created_at",
            },
        )

        task_serializer_data = TaskListPublicSerializer(
            paginated_queryset.get("queryset"), many=True
        ).data

        return CustomResponse().paginated_response(
            data=task_serializer_data,
            pagination=paginated_queryset.get("pagination"),
        )


class TaskListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    @extend_schema(
        tags=['Dashboard - Task'],
        description="Retrieve Task List.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        task_queryset = TaskList.objects.select_related(
            "created_by", "updated_by", "channel", "type", "level", "ig", "org"
        ).all()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            task_queryset,
            request,
            search_fields=[
                "hashtag",
                "title",
                "description",
                "karma",
                "channel__name",
                "type__title",
                "active",
                "variable_karma",
                "usage_count",
                "level__name",
                "org__title",
                "ig__name",
                "event",
                "updated_at",
                "updated_by__full_name",
                "created_by__full_name",
                "created_at",
            ],
            sort_fields={
                "hashtag": "hashtag",
                "title": "title",
                "description": "description",
                "karma": "karma",
                "channels": "channel__name",
                "type": "type__title",
                "active": "active",
                "variable_karma": "variable_karma",
                "usage_count": "usage_count",
                "level": "level__name",
                "org": "org__title",
                "ig": "ig__name",
                "event": "event",
                "updated_at": "updated_at",
                "updated_by": "updated_by__full_name",
                "created_by": "created_by__full_name",
                "created_at": "created_at",
            },
        )

        task_serializer_data = TaskListSerializer(
            paginated_queryset.get("queryset"), many=True
        ).data

        return CustomResponse().paginated_response(
            data=task_serializer_data,
            pagination=paginated_queryset.get("pagination"),
        )

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    @extend_schema(
        tags=['Dashboard - Task'],
        description="Create Task List.",
        request=TaskModifySerializer,
        responses={200: CustomResponseSerializer},
    )
    def post(self, request):  # create
        user_id = JWTUtils.fetch_user_id(request)

        mutable_data = request.data.copy()  # Create a mutable copy of request.data
        mutable_data["created_by"] = user_id
        mutable_data["updated_by"] = user_id
        
        # Extract skill_ids before serializer processing
        skill_ids = mutable_data.pop("skill_ids", None)
        if isinstance(skill_ids, str):
            import json
            try:
                skill_ids = json.loads(skill_ids)
            except:
                skill_ids = []

        serializer = TaskModifySerializer(data=mutable_data)

        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        task = serializer.save()
        
        # Handle skill links
        if skill_ids:
            self._save_task_skills(task.id, skill_ids, user_id)
        
        return CustomResponse(
            general_message="Task Created Successfully"
        ).get_success_response()
    
    def _save_task_skills(self, task_id, skill_ids, user_id):
        """Save skill links for a task"""
        # Clear existing links
        TaskSkillLink.objects.filter(task_id=task_id).delete()
        
        # Create new links
        for skill_id in skill_ids:
            if Skill.objects.filter(id=skill_id, is_active=True).exists():
                TaskSkillLink.objects.create(
                    id=str(uuid.uuid4()),
                    task_id=task_id,
                    skill_id=skill_id,
                    created_by_id=user_id,
                )


class TaskAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    @extend_schema(
        tags=['Dashboard - Task'],
        description="Retrieve Task.",
        responses={200: TaskModifySerializer},
    )
    def get(self, request, task_id):
        task_queryset = TaskList.objects.get(pk=task_id)
        task_serializer = TaskModifySerializer(task_queryset, many=False)
        return CustomResponse(response=task_serializer.data).get_success_response()

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    @extend_schema(tags=['Dashboard - Task'], description="Update Task.",
        responses={200: TaskModifySerializer},
    )
    def put(self, request, task_id):  # edit

        user_id = JWTUtils.fetch_user_id(request)
        mutable_data = request.data.copy()  # Create a mutable copy of request.data
        mutable_data["updated_by"] = user_id
        
        # Extract skill_ids before serializer processing
        skill_ids = mutable_data.pop("skill_ids", None)
        if isinstance(skill_ids, str):
            import json
            try:
                skill_ids = json.loads(skill_ids)
            except:
                skill_ids = None

        task = TaskList.objects.get(pk=task_id)

        serializer = TaskModifySerializer(task, data=mutable_data, partial=True)

        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        serializer.save()
        
        # Handle skill links if provided
        if skill_ids is not None:
            self._save_task_skills(task_id, skill_ids, user_id)

        return CustomResponse(general_message=serializer.data).get_success_response()
    
    def _save_task_skills(self, task_id, skill_ids, user_id):
        """Save skill links for a task"""
        # Clear existing links
        TaskSkillLink.objects.filter(task_id=task_id).delete()
        
        # Create new links
        for skill_id in skill_ids:
            if Skill.objects.filter(id=skill_id, is_active=True).exists():
                TaskSkillLink.objects.create(
                    id=str(uuid.uuid4()),
                    task_id=task_id,
                    skill_id=skill_id,
                    created_by_id=user_id,
                )

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    @extend_schema(tags=['Dashboard - Task'], description="Delete Task.",
        responses={200: TaskModifySerializer},
    )
    def delete(self, request, task_id):  # delete
        task = TaskList.objects.get(id=task_id)
        task.delete()

        return CustomResponse(
            general_message="Task deleted successfully"
        ).get_success_response()


class TaskListCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    @extend_schema(
        tags=['Dashboard - Task'],
        description="Retrieve Task List C S V.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        task_queryset = TaskList.objects.select_related(
            "created_by", "updated_by", "channel", "type", "level", "ig", "org"
        ).all()

        task_serializer_data = TaskListSerializer(task_queryset, many=True).data

        return CommonUtils.generate_csv(task_serializer_data, "Task List")


class ImportTaskListCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    @extend_schema(
        tags=['Dashboard - Task'],
        description="Create Import Task List C S V.",
        request=TaskImportSerializer,
        responses={200: TaskImportSerializer},
    )
    def post(self, request):
        try:
            file_obj = request.FILES["task_list"]
        except KeyError:
            return CustomResponse(
                general_message="File not found."
            ).get_failure_response()

        excel_data = ImportCSV()
        excel_data = excel_data.read_excel_file(file_obj)

        if not excel_data:
            return CustomResponse(
                general_message="Empty csv file."
            ).get_failure_response()

        temp_headers = [
            "hashtag",
            "title",
            "description",
            "karma",
            "usage_count",
            "variable_karma",
            "level",
            "channel",
            "type",
            "ig",
            "org",
            "event",
        ]
        first_entry = excel_data[0]
        for key in temp_headers:
            if key not in first_entry:
                return CustomResponse(
                    general_message=f"{key} does not exist in the file."
                ).get_failure_response()

        excel_data = [row for row in excel_data if any(row.values())]
        valid_rows = []
        error_rows = []

        hashtags_excel = set()
        hashtags_db = TaskList.objects.values_list("hashtag", flat=True)
        channels_to_fetch = set()
        task_types_to_fetch = set()
        levels_to_fetch = set()
        igs_to_fetch = set()
        orgs_to_fetch = set()

        for row in excel_data[1:]:
            hashtag = row.get("hashtag")
            if not hashtag:
                row["error"] = "Missing hashtag."
                error_rows.append(row)
                excel_data.remove(row)
                continue
            elif hashtag in hashtags_excel:
                row["error"] = f"Duplicate hashtag in excel: {hashtag}"
                error_rows.append(row)
                excel_data.remove(row)
                continue
            elif hashtag in hashtags_db:
                row["error"] = f"Duplicate hashtag in database: {hashtag}"
                error_rows.append(row)
                excel_data.remove(row)
                continue
            else:
                hashtags_excel.add(hashtag)

            title = row.get("title")
            if not title:
                row["error"] = "Missing title."
                error_rows.append(row)
                excel_data.remove(row)
                continue

            level = row.get("level")
            channel = row.get("channel")
            task_type = row.get("type")
            ig = row.get("ig")
            org = row.get("org")

            channels_to_fetch.add(channel)
            task_types_to_fetch.add(task_type)
            levels_to_fetch.add(level)
            igs_to_fetch.add(ig)
            orgs_to_fetch.add(org)

        channels = Channel.objects.filter(name__in=channels_to_fetch).values(
            "id", "name"
        )

        task_types = TaskType.objects.filter(title__in=task_types_to_fetch).values(
            "id", "title"
        )

        levels = Level.objects.filter(name__in=levels_to_fetch).values("id", "name")

        igs = InterestGroup.objects.filter(name__in=igs_to_fetch).values("id", "name")

        orgs = Organization.objects.filter(code__in=orgs_to_fetch).values("id", "code")

        channels_dict = {channel["name"]: channel["id"] for channel in channels}
        task_types_dict = {
            task_type["title"]: task_type["id"] for task_type in task_types
        }
        levels_dict = {level["name"]: level["id"] for level in levels}
        igs_dict = {ig["name"]: ig["id"] for ig in igs}
        orgs_dict = {org["code"]: org["id"] for org in orgs}
        events = Events.get_all_values()

        for row in excel_data[1:]:
            level = row.pop("level")
            channel = row.pop("channel")
            task_type = row.pop("type")
            ig = row.pop("ig")
            org = row.pop("org")

            task_type_id = task_types_dict.get(task_type)
            channel_id = channels_dict.get(channel) if channel is not None else None
            level_id = levels_dict.get(level) if level is not None else None
            ig_id = igs_dict.get(ig) if ig is not None else None
            org_id = orgs_dict.get(org) if org is not None else None
            event = row.get("event")

            if channel and not channel_id:
                row["error"] = f"Invalid channel: {channel}"
                error_rows.append(row)
            elif not task_type_id:
                row["error"] = f"Invalid task type: {task_type}"
                error_rows.append(row)
            elif level and not level_id:
                row["error"] = f"Invalid level: {level}"
                error_rows.append(row)
            elif ig and not ig_id:
                row["error"] = f"Invalid interest group: {ig}"
                error_rows.append(row)
            elif org and not org_id:
                row["error"] = f"Invalid organization: {org}"
                error_rows.append(row)
            elif event is not None and event not in events:
                row["error"] = f"Invalid event: {event}"
                error_rows.append(row)
            else:
                user_id = JWTUtils.fetch_user_id(request)
                row["id"] = str(uuid.uuid4())
                row["updated_by_id"] = user_id
                row["updated_at"] = DateTimeUtils.get_current_utc_time()
                row["created_by_id"] = user_id
                row["created_at"] = DateTimeUtils.get_current_utc_time()
                row["active"] = True
                row["channel_id"] = channel_id or None
                row["type_id"] = task_type_id
                row["level_id"] = level_id or None
                row["ig_id"] = ig_id or None
                row["org_id"] = org_id or None
                valid_rows.append(row)

        task_list_serializer = TaskImportSerializer(data=valid_rows, many=True)
        success_data = []
        if task_list_serializer.is_valid():
            task_list_serializer.save()
            for task_data in task_list_serializer.data:
                success_data.append(
                    {
                        "hashtag": task_data.get("hashtag", ""),
                        "title": task_data.get("title", ""),
                        "description": task_data.get("description", ""),
                        "karma": task_data.get("karma", ""),
                        "usage_count": task_data.get("usage_count", ""),
                        "variable_karma": task_data.get("variable_karma", ""),
                        "level": task_data.get("level_id", ""),
                        "channel": task_data.get("channel_id", ""),
                        "type": task_data.get("type_id", ""),
                        "ig": task_data.get("ig_id", ""),
                        "org": task_data.get("org_id", ""),
                        "event": task_data.get("event", ""),
                    }
                )
        else:
            error_rows.append(task_list_serializer.errors)

        return CustomResponse(
            response={"Success": success_data, "Failed": error_rows}
        ).get_success_response()


class ChannelDropdownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    @extend_schema(tags=['Dashboard - Task'], description="Retrieve Channel Dropdown.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        channels = Channel.objects.values("id", "name")

        return CustomResponse(response=channels).get_success_response()


class IGDropdownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    @extend_schema(tags=['Dashboard - Task'], description="Retrieve I G Dropdown.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        igs = InterestGroup.objects.values("id", "name")
        return CustomResponse(response=igs).get_success_response()


class OrganizationDropdownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    @extend_schema(tags=['Dashboard - Task'], description="Retrieve Organization Dropdown.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        organizations = Organization.objects.values("id", "title")
        return CustomResponse(response=organizations).get_success_response()


class LevelDropdownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    @extend_schema(tags=['Dashboard - Task'], description="Retrieve Level Dropdown.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        levels = Level.objects.values("id", "name")
        return CustomResponse(response=levels).get_success_response()


class TaskTypesDropDownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    @extend_schema(tags=['Dashboard - Task'], description="Retrieve Task Types Drop Down.",
        responses={200: TasktypeSerializer},
    )
    def get(self, request):
        task_types = TaskType.objects.values("id", "title")
        return CustomResponse(response=task_types).get_success_response()


class EventDropDownApi(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
        ]
    )
    @extend_schema(tags=['Dashboard - Task'], description="Retrieve Event Drop Down Api.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        events = Events.get_all_values()
        return CustomResponse(response=events).get_success_response()


class TaskBaseTemplateAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Task'], description="Retrieve Task Base Template.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        wb = load_workbook("./excel-templates/task_base_template.xlsx")
        ws = wb["Data Definitions"]
        levels = Level.objects.all().values_list("name", flat=True)
        channels = Channel.objects.all().values_list("name", flat=True)
        task_types = TaskType.objects.all().values_list("title", flat=True)
        igs = InterestGroup.objects.all().values_list("name", flat=True)
        orgs = Organization.objects.all().values_list("code", flat=True)
        events = Events.get_all_values()

        data = {
            "level": levels,
            "channel": channels,
            "type": task_types,
            "ig": igs,
            "org": orgs,
            "event": events,
        }
        # Write data column-wise
        for col_num, (col_name, col_values) in enumerate(data.items(), start=1):
            for row, value in enumerate(col_values, start=2):
                ws.cell(row=row, column=col_num, value=value)
        # Save the file
        with NamedTemporaryFile() as tmp:
            tmp.close()  # with statement opened tmp, close it so wb.save can open it
            wb.save(tmp.name)
            with open(tmp.name, "rb") as f:
                f.seek(0)
                new_file_object = f.read()
        return FileResponse(
            BytesIO(new_file_object),
            as_attachment=True,
            filename="task_base_template.xlsx",
        )


class TaskTypeCrudAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
        ]
    )
    @extend_schema(
        tags=['Dashboard - Task'],
        description="Retrieve Task Type Crud.",
        responses={200: TasktypeSerializer},
    )
    def get(self, request):
        taskType = TaskType.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            taskType,
            request,
            ["title"],
            {
                "title": "title",
                "updated_by": "updated_by",
                "created_by": "created_by",
                "updated_at": "updated_at",
                "created_at": "created_at",
            },
        )
        serializer = TasktypeSerializer(paginated_queryset.get("queryset"), many=True)

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Task'],
        description="Create Task Type Crud.",
        request=TaskTypeCreateUpdateSerializer,
        responses={200: TasktypeSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = TaskTypeCreateUpdateSerializer(
            data=request.data, context={"user_id": user_id}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Task type added successfully"
            ).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Task'], description="Delete Task Type Crud.",
        responses={200: TasktypeSerializer},
    )
    def delete(self, request, task_type_id):
        taskType = TaskType.objects.filter(id=task_type_id).first()
        if taskType is None:
            return CustomResponse(
                general_message="task type doesnt exist"
            ).get_failure_response()
        taskType.delete()
        return CustomResponse(
            general_message=f"{taskType.title} Deleted Successfully"
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Task'],
        description="Update Task Type Crud.",
        responses={200: TaskTypeCreateUpdateSerializer},
    )
    def put(self, request, task_type_id):
        taskType = TaskType.objects.filter(id=task_type_id).first()
        if taskType is None:
            return CustomResponse(
                general_message="task type not found"
            ).get_failure_response()
        serializer = TaskTypeCreateUpdateSerializer(
            taskType, data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message=f"{taskType.title} updated successfully"
            ).get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()


# ---------------------------------------------------------------------------
# Admin: Task Approval Workflow (for company-submitted tasks)
# ---------------------------------------------------------------------------

class AdminTaskApprovalAPI(APIView):
    """
    GET  /dashboard/task/pending/              — list all tasks awaiting admin review
    PATCH /dashboard/task/<task_id>/approve/   — approve a pending task (goes live)
    PATCH /dashboard/task/<task_id>/reject/    — reject with a reason

    All actions require the Admin role.
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Task'], description="Retrieve Admin Task Approval.",
        responses={200: CustomResponseSerializer},
    )
    def get(self, request):
        """List all tasks with approval_status='pending'."""
        from django.utils import timezone as tz

        queryset = (
            TaskList.objects
            .filter(approval_status="pending")
            .select_related("ig", "type", "submitted_by_company")
            .order_by("created_at")
        )

        paginated = CommonUtils.get_paginated_queryset(
            queryset,
            request,
            search_fields=["title", "hashtag", "submitted_by_company__name"],
            sort_fields={"createdAt": "created_at", "title": "title"},
            is_pagination=True,
        )

        data = []
        for task in paginated["queryset"]:
            data.append({
                "id":                   str(task.id),
                "title":                task.title,
                "hashtag":              task.hashtag,
                "description":          task.description,
                "karma":                task.karma,
                "approval_status":      task.approval_status,
                "ig":                   {"id": str(task.ig.id), "name": task.ig.name} if task.ig else None,
                "type":                 {"id": str(task.type.id), "title": task.type.title} if task.type else None,
                "submitted_by_company": {
                    "id": str(task.submitted_by_company.id),
                    "name": task.submitted_by_company.name,
                } if task.submitted_by_company else None,
                "created_at":           task.created_at.isoformat(),
            })

        return CustomResponse(
            general_message="Pending tasks fetched successfully.",
            response={"tasks": data, "pagination": paginated["pagination"]},
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(tags=['Dashboard - Task'], description="Partially update Admin Task Approval.",
        responses={200: CustomResponseSerializer},
    )
    def patch(self, request, task_id):
        """
        Approve or reject a pending task.
        Body: { "action": "approve" | "reject", "reason": "<string — required for reject>" }
        """
        from django.utils import timezone as tz

        action = request.data.get("action")
        if action not in ("approve", "reject"):
            return CustomResponse(
                general_message="Invalid action. Must be 'approve' or 'reject'.",
                message={"error_code": "INVALID_ACTION"},
            ).get_failure_response()

        try:
            task = TaskList.objects.get(id=task_id)
        except TaskList.DoesNotExist:
            return CustomResponse(
                general_message="Task not found.",
                message={"error_code": "TASK_NOT_FOUND"},
            ).get_failure_response()

        if task.approval_status != "pending":
            return CustomResponse(
                general_message=f"Only pending tasks can be reviewed. Current status: '{task.approval_status}'.",
                message={"error_code": "INVALID_STATUS_TRANSITION"},
            ).get_failure_response()

        admin_user_id = JWTUtils.fetch_user_id(request)
        from db.user import User as UserModel
        admin_user = UserModel.objects.filter(id=admin_user_id).first()

        now = tz.now()

        if action == "approve":
            task.approval_status = "approved"
            task.active = True
            task.rejection_reason = None
            task.reviewed_by_admin = admin_user
            task.reviewed_at = now
            task.updated_by = admin_user
            task.save(update_fields=[
                "approval_status", "active", "rejection_reason",
                "reviewed_by_admin", "reviewed_at", "updated_by", "updated_at",
            ])
            message = "Task approved and is now live."
        else:
            reason = (request.data.get("reason") or "").strip()
            if not reason:
                return CustomResponse(
                    general_message="A rejection reason is required.",
                    message={"error_code": "REASON_REQUIRED"},
                ).get_failure_response()
            task.approval_status = "rejected"
            task.active = False
            task.rejection_reason = reason
            task.reviewed_by_admin = admin_user
            task.reviewed_at = now
            task.updated_by = admin_user
            task.save(update_fields=[
                "approval_status", "active", "rejection_reason",
                "reviewed_by_admin", "reviewed_at", "updated_by", "updated_at",
            ])
            message = "Task rejected."

        return CustomResponse(
            general_message=message,
            response={
                "task_id":          str(task.id),
                "approval_status":  task.approval_status,
                "active":           task.active,
                "rejection_reason": task.rejection_reason,
                "reviewed_by":      str(admin_user.id) if admin_user else None,
                "reviewed_at":      task.reviewed_at.isoformat() if task.reviewed_at else None,
            },
        ).get_success_response()
