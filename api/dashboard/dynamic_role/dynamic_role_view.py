from rest_framework.views import APIView

from db.user import Role, DynamicRole
from db.user import User

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from .dynamic_role_serializer import DynamicRoleCreateSerializer, DynamicRoleListSerializer

import uuid
from utils.utils import DateTimeUtils

class DynamicRoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request): # create
        type = request.data['type']
        role = Role.objects.filter(title=request.data['role']).first()
        if role:
            role = role.id
        else:
            return CustomResponse(general_message='Role does not exist').get_failure_response()
        data = {'type': type, 'role': role}
        serializer = DynamicRoleCreateSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Dynamic Role created successfully', response=serializer.data).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    def get(self, request): # list
        #dynamic_role_queryset = DynamicRole.objects.all()
        dynamic_roles = DynamicRole.objects.values('type', 'role__title').distinct()

        roles_by_type = {}
        for entry in dynamic_roles:
            role_type = entry['type']
            role_title = entry['role__title']

            if role_type not in roles_by_type:
                roles_by_type[role_type] = []

            roles_by_type[role_type].append(role_title)
        data = []
        for type, roles in roles_by_type.items():
            data.append({'type': type, 'role': roles})

        serializer = DynamicRoleListSerializer(data, many=True)
        return CustomResponse(response=serializer.data).get_success_response()
        # serializer = DynamicRoleListSerializer(dynamic_role_queryset, many=True)
        # return CustomResponse(response=serializer.data).get_success_response()
