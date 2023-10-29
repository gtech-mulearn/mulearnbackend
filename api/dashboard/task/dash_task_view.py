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

        request.data["created_by"] = request.data["updated_by"] = user_id
        serializer = TaskModifySerializer(data=request.data)

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
        request.data["updated_by"] = user_id

        task = TaskList.objects.get(pk=task_id)

        serializer = TaskModifySerializer(
            task,
            data=request.data,
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
            "channels",
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
            "channels",
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

        valid_rows = []
        error_rows = []

        channels_to_fetch = set()
        task_types_to_fetch = set()
        levels_to_fetch = set()
        igs_to_fetch = set()
        orgs_to_fetch = set()

        for row in excel_data[1:]:
            hashtag = row.get("hashtag")
            level = row.get("level")
            channel = row.get("channels")
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

        for row in excel_data[1:]:
            hashtag = row.get("hashtag")
            level = row.pop("level")
            channel = row.pop("channels")
            task_type = row.pop("type")
            ig = row.pop("ig")
            org = row.pop("org")

            channel_id = channels_dict.get(channel)
            task_type_id = task_types_dict.get(task_type)
            level_id = levels_dict.get(level) if level is not None else None
            ig_id = igs_dict.get(ig) if ig is not None else None
            org_id = orgs_dict.get(org) if org is not None else None

            if TaskList.objects.filter(hashtag=hashtag).exists():
                row["error"] = f"Hashtag already exists: {hashtag}"
                error_rows.append(row)
            elif not channel_id:
                row["error"] = f"Invalid channels ID: {channel}"
                error_rows.append(row)
            elif not task_type_id:
                row["error"] = f"Invalid task type ID: {task_type}"
                error_rows.append(row)
            elif level and not level_id:
                row["error"] = f"Invalid level ID: {level}"
                error_rows.append(row)
            elif ig and not ig_id:
                row["error"] = f"Invalid interest group ID: {ig}"
                error_rows.append(row)
            elif org and not org_id:
                row["error"] = f"Invalid organization ID: {org}"
                error_rows.append(row)
            else:
                user_id = JWTUtils.fetch_user_id(request)
                row["id"] = str(uuid.uuid4())
                row["updated_by_id"] = user_id
                row["updated_at"] = DateTimeUtils.get_current_utc_time()
                row["created_by_id"] = user_id
                row["created_at"] = DateTimeUtils.get_current_utc_time()
                row["active"] = True
                row["channel_id"] = channel_id
                row["type_id"] = task_type_id
                row["level_id"] = level_id or None
                row["ig_id"] = ig_id or None
                row["org_id"] = org_id or None
                valid_rows.append(row)

        task_list_serializer = TaskImportSerializer(data=valid_rows, many=True)
        if task_list_serializer.is_valid():
            task_list_serializer.save()
        else:
            error_rows.append(task_list_serializer.errors)

        return CustomResponse(
            response={"Success": task_list_serializer.data, "Failed": error_rows}
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
