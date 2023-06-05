import uuid

from openpyxl import Workbook
from rest_framework.views import APIView
from db.task import TaskList, Channel, TaskType, Level, InterestGroup
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils, ImportCSV
from .dash_task_serializer import TaskListSerializer
from db.user import User


class TaskApi(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        task_serializer = TaskList.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(task_serializer, request, ["id",
                                                                                           "hashtag",
                                                                                           "title",
                                                                                           "karma",
                                                                                           "channel",
                                                                                           "type",
                                                                                           "active",
                                                                                           "variable_karma",
                                                                                           "usage_count",
                                                                                           "created_by",
                                                                                           "created_at"])
        task_serializer_data = TaskListSerializer(paginated_queryset.get('queryset'), many=True).data

        return CustomResponse().paginated_response(data=task_serializer_data,
                                                   pagination=paginated_queryset.get('pagination'))

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request):  # create
        user_id = JWTUtils.fetch_user_id(request)
        task_data = TaskList.objects.create(
            id=uuid.uuid4(),
            hashtag=request.data.get('hashtag'),
            title=request.data.get('title'),
            description=request.data.get('description'),
            karma=request.data.get('karma'),
            channel=request.data.get('channel'),
            active=request.data.get('active'),
            variable_karma=request.data.get('variable_karma'),
            usage_count=request.data.get('usage_count'),
            level=request.data.get('level'),
            ig=request.data.get('ig'),
            updated_by_id=user_id,
            updated_at=DateTimeUtils.get_current_utc_time(),
            created_by_id=user_id,
            created_at=DateTimeUtils.get_current_utc_time())
        serializer = TaskListSerializer(task_data)
        return CustomResponse(response={"taskList": serializer.data}).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def put(self, request, pk):  # edit
        user_id = JWTUtils.fetch_user_id(request)
        taskData = TaskList.objects.filter(id=pk).first()
        fields_to_update = ["hashtag",
                            "title",
                            "karma",
                            "active",
                            "variable_karma",
                            "usage_count"]
        for field in fields_to_update:
            if field in request.data:
                setattr(taskData, field, request.data[field])
        taskData.updated_by = User.objects.filter(id=user_id).first()
        taskData.updated_at = DateTimeUtils.get_current_utc_time()
        taskData.save()
        serializer = TaskListSerializer(taskData)
        return CustomResponse(
            response={"taskList": serializer.data}
        ).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def patch(self, request, pk):  # delete
        user_id = JWTUtils.fetch_user_id(request)
        taskData = TaskList.objects.filter(id=pk).first()
        taskData.active = False
        taskData.updated_by = user_id
        taskData.updated_at = DateTimeUtils.get_current_utc_time()
        taskData.save()
        serializer = TaskListSerializer(taskData)
        return CustomResponse(
            response={"taskList": serializer.data}
        ).get_success_response()


class TaskListCSV(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def get(self, request):
        task_serializer = TaskList.objects.all()
        task_serializer_data = TaskListSerializer(task_serializer, many=True).data

        return CommonUtils.generate_csv(task_serializer_data, 'Task List')


class ImportTaskListCSV(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request):
        try:
            file_obj = request.FILES['task_list']
        except KeyError:
            return CustomResponse(response={'task_list file not found'}).get_failure_response()

        excel_data = ImportCSV.read_excel_file(file_obj)
        if not excel_data:
            return CustomResponse(response={'Empty csv file'}).get_failure_response()

        valid_rows = []
        error_rows = []

        for row in excel_data:
            hashtag = row.get('hashtag')
            level_id = row.get('level_id')
            channel_id = row.get('channel_id')
            type_id = row.get('type_id')
            ig_id = row.get('ig_id')

            if TaskList.objects.filter(hashtag=hashtag).exists():
                row['error'] = f"Hashtag already exists: {hashtag}"
                error_rows.append(row)
            elif not Channel.objects.filter(id=channel_id).exists():
                row['error'] = f"Invalid Channel_id: {channel_id}"
                error_rows.append(row)
            elif not TaskType.objects.filter(id=type_id).exists():
                row['error'] = f"Invalid Type_id: {type_id}"
                error_rows.append(row)
            elif level_id is not None and not Level.objects.filter(id=level_id).exists():
                row['error'] = f"Invalid Level_id: {level_id}"
                error_rows.append(row)
            elif ig_id is not None and not InterestGroup.objects.filter(id=ig_id).exists():
                row['error'] = f"Invalid InterestGroup_id: {ig_id}"
                error_rows.append(row)
            else:
                valid_rows.append(row)

        if not valid_rows:
            return CustomResponse(response={'No valid rows found'}).get_failure_response()

        workbook = Workbook()
        valid_sheet = workbook.active
        valid_headers = list(valid_rows[0].keys())
        valid_sheet.append(valid_headers)

        error_sheet = workbook.create_sheet(title='Invalid Rows')
        error_headers = list(error_rows[0].keys())
        error_sheet.append(error_headers)

        for row in valid_rows:
            valid_sheet.append([row.get(header, '') for header in valid_headers])

        for row in error_rows:
            error_sheet.append([row.get(header, '') for header in error_headers])

        excel_path = 'csv_data.xlsx'
        workbook.save(excel_path)

        for row in valid_rows:
            user_id = JWTUtils.fetch_user_id(request)
            row['updated_by_id'] = user_id
            row['updated_at'] = str(DateTimeUtils.get_current_utc_time())
            row['created_by_id'] = user_id
            row['created_at'] = str(DateTimeUtils.get_current_utc_time())
            TaskList.objects.create(**row)
        return CustomResponse(response={"Success": valid_rows , "Failed": error_rows}).get_success_response()
