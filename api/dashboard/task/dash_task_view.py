import uuid

from rest_framework.views import APIView

from db.organization import Organization
from db.task import Channel, InterestGroup, Level, TaskList, TaskType
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import Events, RoleType
from utils.utils import CommonUtils, DateTimeUtils, ImportCSV
from .dash_task_serializer import (
    TaskImportSerializer,
    TaskListSerializer,
    TaskModifySerializer,
    TaskTypeCreateUpdateSerializer,
    TasktypeSerializer,
)

from openpyxl import load_workbook
from tempfile import NamedTemporaryFile
from io import BytesIO
from django.http import FileResponse


class TaskListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    def get(self, request):
        task_queryset = TaskList.objects.select_related(
            "created_by",
            "updated_by",
            "channel",
            "type",
            "level",
            "ig",
            "org"
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
                "updated_by__first_name",
                "created_by__first_name",
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
                "updated_by": "updated_by__first_name",
                "created_by": "created_by__first_name",
                "created_at": "created_at",
            },
        )

        task_serializer_data = TaskListSerializer(
            paginated_queryset.get("queryset"),
            many=True
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
    def post(self, request):  # create
        user_id = JWTUtils.fetch_user_id(request)

        mutable_data = request.data.copy()  # Create a mutable copy of request.data
        mutable_data["created_by"] = user_id
        mutable_data["updated_by"] = user_id

        serializer = TaskModifySerializer(data=mutable_data)

        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors
            ).get_failure_response()

        serializer.save()
        return CustomResponse(
            general_message="Task Created Successfully"
        ).get_success_response()


class TaskAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
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
    def put(self, request, task_id):  # edit

        user_id = JWTUtils.fetch_user_id(request)
        mutable_data = request.data.copy()  # Create a mutable copy of request.data
        mutable_data["updated_by"] = user_id

        task = TaskList.objects.get(pk=task_id)

        serializer = TaskModifySerializer(
            task,
            data=mutable_data,
            partial=True
        )

        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors
            ).get_failure_response()

        serializer.save()

        return CustomResponse(
            general_message=serializer.data
        ).get_success_response()

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
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
    def get(self, request):
        task_queryset = TaskList.objects.select_related(
            "created_by",
            "updated_by",
            "channel",
            "type",
            "level",
            "ig",
            "org"
        ).all()

        task_serializer_data = TaskListSerializer(
            task_queryset,
            many=True
        ).data

        return CommonUtils.generate_csv(
            task_serializer_data,
            "Task List"
        )


class ImportTaskListCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
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

        channels = Channel.objects.filter(
            name__in=channels_to_fetch
        ).values(
            "id",
            "name"
        )

        task_types = TaskType.objects.filter(
            title__in=task_types_to_fetch
        ).values(
            "id",
            "title"
        )

        levels = Level.objects.filter(
            name__in=levels_to_fetch
        ).values(
            "id",
            "name"
        )

        igs = InterestGroup.objects.filter(
            name__in=igs_to_fetch
        ).values(
            "id",
            "name"
        )

        orgs = Organization.objects.filter(
            code__in=orgs_to_fetch
        ).values(
            "id",
            "code"
        )

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
                success_data.append({
                    'hashtag': task_data.get('hashtag', ''),
                    'title': task_data.get('title', ''),
                    'description': task_data.get('description', ''),
                    'karma': task_data.get('karma', ''),
                    'usage_count': task_data.get('usage_count', ''),
                    'variable_karma': task_data.get('variable_karma', ''),
                    'level': task_data.get('level_id', ''),
                    'channel': task_data.get('channel_id', ''),
                    'type': task_data.get('type_id', ''),
                    'ig': task_data.get('ig_id', ''),
                    'org': task_data.get('org_id', ''),
                    'event': task_data.get('event', ''),
                })
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
    def get(self, request):
        channels = Channel.objects.values(
            "id",
            "name"
        )

        return CustomResponse(
            response=channels
        ).get_success_response()


class IGDropdownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    def get(self, request):
        igs = InterestGroup.objects.values(
            "id",
            "name"
        )
        return CustomResponse(
            response=igs
        ).get_success_response()


class OrganizationDropdownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    def get(self, request):
        organizations = Organization.objects.values(
            "id",
            "title"
        )
        return CustomResponse(
            response=organizations
        ).get_success_response()


class LevelDropdownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    def get(self, request):
        levels = Level.objects.values(
            "id",
            "name"
        )
        return CustomResponse(
            response=levels
        ).get_success_response()


class TaskTypesDropDownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
            RoleType.FELLOW.value,
            RoleType.ASSOCIATE.value,
        ]
    )
    def get(self, request):
        task_types = TaskType.objects.values(
            "id",
            "title"
        )
        return CustomResponse(
            response=task_types
        ).get_success_response()


class EventDropDownApi(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
        ]
    )
    def get(self, request):
        events = Events.get_all_values()
        return CustomResponse(
            response=events
        ).get_success_response()


class TaskBaseTemplateAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        wb = load_workbook('./excel-templates/task_base_template.xlsx')
        ws = wb['Data Definitions']
        levels = Level.objects.all().values_list('name', flat=True)
        channels = Channel.objects.all().values_list('name', flat=True)
        task_types = TaskType.objects.all().values_list('title', flat=True)
        igs = InterestGroup.objects.all().values_list('name', flat=True)
        orgs = Organization.objects.all().values_list('code', flat=True)
        events = Events.get_all_values()

        data = {
            'level': levels,
            'channel': channels,
            'type': task_types,
            'ig': igs,
            'org': orgs,
            'event': events
        }
        # Write data column-wise
        for col_num, (col_name, col_values) in enumerate(data.items(), start=1):
            for row, value in enumerate(col_values, start=2):
                ws.cell(row=row, column=col_num, value=value)
        # Save the file
        with NamedTemporaryFile() as tmp:
            tmp.close()  # with statement opened tmp, close it so wb.save can open it
            wb.save(tmp.name)
            with open(tmp.name, 'rb') as f:
                f.seek(0)
                new_file_object = f.read()
        return FileResponse(BytesIO(new_file_object), as_attachment=True, filename='task_base_template.xlsx')


class TaskTypeCrudAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [
            RoleType.ADMIN.value,
        ]
    )
    def get(self, request):
        taskType = TaskType.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            taskType, request, ["title"],
            {"title": "title", "updated_by": "updated_by", "created_by": "created_by", "updated_at": "updated_at",
             "created_at": "created_at"}
        )
        serializer = TasktypeSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
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
    def put(self, request, task_type_id):
        taskType = TaskType.objects.filter(id=task_type_id).first()
        if taskType is None:
            return CustomResponse(general_message="task type not found").get_failure_response()
        serializer = TaskTypeCreateUpdateSerializer(
            taskType, data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message=f"{taskType.title} updated successfully"
            ).get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()
