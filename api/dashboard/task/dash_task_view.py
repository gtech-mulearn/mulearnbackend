import uuid

from django.db.models import F
from rest_framework.views import APIView

from db.organization import Organization
from db.task import TaskList, Channel, TaskType, Level, InterestGroup
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils, ImportCSV
from .dash_task_serializer import TaskListSerializer, TaskUpdateSerializer, TaskCreateSerializer, \
    ChannelDropdownSerializer, IGDropdownSerializer, OrganizationDropdownSerialize, LevelDropdownSerialize, \
    TaskTypeDropdownSerializer


class TaskApi(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        task_queryset = TaskList.objects.annotate(
            channel_name=F('channel__name'),
            org_title=F('org__title'),
            updated_by_first_name=F('updated_by__first_name'),
            updated_by_last_name=F('updated_by__last_name'),
            created_by_first_name=F('created_by__first_name'),
            created_by_last_name=F('created_by__last_name')
        )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            task_queryset, request,
            search_fields=["title", "channel_name", "org_title", "description", "karma", "usage_count",
                           "updated_by_first_name", "updated_by_last_name",
                           "created_by_first_name", "created_by_last_name"],
            sort_fields={'title': 'title', 'karma': 'karma', 'updated_by': 'updated_by',
                         'updated_at': 'updated_at', 'created_at': 'created_at'}
        )

        task_serializer_data = TaskListSerializer(paginated_queryset.get('queryset'), many=True).data

        return CustomResponse().paginated_response(data=task_serializer_data,
                                                   pagination=paginated_queryset.get('pagination'))

    @role_required([RoleType.ADMIN.value, ])
    def post(self, request):  # create

        user_id = JWTUtils.fetch_user_id(request)

        serializer = TaskCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Task Created Successfully').get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value, ])
    def put(self, request, task_id):  # edit

        user_id = JWTUtils.fetch_user_id(request)
        task_list = TaskList.objects.filter(id=task_id).first()

        if TaskList is None:
            return CustomResponse(general_message='Invalid task id').get_failure_response()

        serializer = TaskUpdateSerializer(task_list, data=request.data,
                                          context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Task Edited Successfully').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value, ])
    def patch(self, request, pk):  # delete
        user_id = JWTUtils.fetch_user_id(request)
        taskData = TaskList.objects.filter(id=pk).first()
        taskData.active = False
        taskData.updated_by = User.objects.filter(id=user_id).first()
        taskData.updated_at = DateTimeUtils.get_current_utc_time()
        taskData.save()
        serializer = TaskListSerializer(taskData)
        return CustomResponse(
            response={"taskList": serializer.data}
        ).get_success_response()


class TaskListCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request):
        task_serializer = TaskList.objects.all()
        task_serializer_data = TaskListSerializer(task_serializer, many=True).data

        return CommonUtils.generate_csv(task_serializer_data, 'Task List')


class ImportTaskListCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def post(self, request):
        try:
            file_obj = request.FILES['task_list']
        except KeyError:
            return CustomResponse(general_message={'File not found.'}).get_failure_response()

        excel_data = ImportCSV.read_excel_file(file_obj)
        if not excel_data:
            return CustomResponse(general_message={'Empty csv file.'}).get_failure_response()

        temp_headers = ['hashtag', 'title', 'description', 'karma', 'usage_count', 'variable_karma', 'level', 'channel',
                        'type', 'ig', 'org']
        first_entry = excel_data[0]
        for key in temp_headers:
            if key not in first_entry:
                return CustomResponse(general_message={f'{key} does not exist in the file.'}).get_failure_response()

        valid_rows = []
        error_rows = []

        for row in excel_data[1:]:
            hashtag = row.get('hashtag')
            title = row.get('title')
            description = row.get('description')
            karma = row.get('karma')
            usage_count = row.get('usage_count')
            variable_karma = row.get('variable_karma')
            level = row.pop('level')
            channel = row.pop('channel')
            task_type = row.pop('type')
            ig = row.pop('ig')
            org = row.pop('org')

            channel_obj = Channel.objects.filter(name=channel).first()
            task_type_obj = TaskType.objects.filter(title=task_type).first()
            level_obj = Level.objects.filter(name=level).first() if level is not None else None
            ig_obj = InterestGroup.objects.filter(name=ig).first() if ig is not None else None
            org_obj = Organization.objects.filter(code=org).first() if org is not None else None

            if TaskList.objects.filter(hashtag=hashtag).exists():
                row['error'] = f"Hashtag already exists: {hashtag}"
                error_rows.append(row)
            elif not channel_obj:
                row['error'] = f"Invalid channel ID: {channel}"
                error_rows.append(row)
            elif not task_type_obj:
                row['error'] = f"Invalid task type ID: {task_type}"
                error_rows.append(row)
            elif level and not level_obj:
                row['error'] = f"Invalid level ID: {level}"
                error_rows.append(row)
            elif ig and not ig_obj:
                row['error'] = f"Invalid interest group ID: {ig}"
                error_rows.append(row)
            elif org and not org_obj:
                row['error'] = f"Invalid organization ID: {org}"
                error_rows.append(row)
            else:
                user_id = 1
                row['id'] = uuid.uuid4()
                row['updated_by_id'] = user_id
                row['updated_at'] = str(DateTimeUtils.get_current_utc_time())
                row['created_by_id'] = user_id
                row['created_at'] = str(DateTimeUtils.get_current_utc_time())
                row['active'] = True
                row['channel_id'] = channel_obj.id if channel_obj else None
                row['type_id'] = task_type_obj.id if task_type_obj else None
                row['level_id'] = level_obj.id if level_obj else None
                row['ig_id'] = ig_obj.id if ig_obj else None
                row['org_id'] = org_obj.id if ig_obj else None
                TaskList.objects.create(**row)
                print(row)
                valid_rows.append(row)

        return CustomResponse(response={"Success": valid_rows, "Failed": error_rows}).get_success_response()


class TaskGetAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request, pk):
        task_serializer = TaskList.objects.get(id=pk)
        serializer = TaskListSerializer(task_serializer)
        return CustomResponse(response={"Task": serializer.data}).get_success_response()


class ChannelDropdownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request):
        channel = Channel.objects.all()
        serializer = ChannelDropdownSerializer(channel, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class IGDropdownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request):
        ig = InterestGroup.objects.all()
        serializer = IGDropdownSerializer(ig, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class OrganizationDropdownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request):
        organization = Organization.objects.all()
        serializer = OrganizationDropdownSerialize(organization, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class LevelDropdownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request):
        level = Level.objects.all()
        serializer = LevelDropdownSerialize(level, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class TaskTypesDropDownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request):
        task_types = TaskType.objects.all()
        serializer = TaskTypeDropdownSerializer(task_types, many=True)
        return CustomResponse(response=serializer.data).get_success_response()
