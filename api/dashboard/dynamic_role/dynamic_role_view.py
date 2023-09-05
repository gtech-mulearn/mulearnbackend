from rest_framework.views import APIView

from db.user import DynamicRole
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from .dynamic_role_serializer import DynamicRoleCreateSerializer, DynamicRoleListSerializer, DynamicRoleUpdateSerializer
from utils.utils import CommonUtils
from utils.types import RoleType

class DynamicRoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request): # create
        serializer = DynamicRoleCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Dynamic Role created successfully', response=serializer.data).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def get(self, request):    # list
        dynamic_roles = DynamicRole.objects.values('type').distinct()
        data = [{'type': role['type']} for role in dynamic_roles]

        paginated_queryset = CommonUtils.get_paginated_queryset(
            data, request,
            search_fields=["type", "role__title",],
            sort_fields={'type':'type',
                            'role':'role__title'}
        )
        dynamic_role_serializer = DynamicRoleListSerializer(paginated_queryset.get('queryset'), many=True).data
        return CustomResponse().paginated_response(data=dynamic_role_serializer,
                                                   pagination=paginated_queryset.get('pagination')) 

    @role_required([RoleType.ADMIN.value])
    def delete(self, request): # delete
        type = request.data['type']
        role = request.data['role']
        if dynamic_role := DynamicRole.objects.filter(type=type, role__title=role).first():
            dynamic_role.delete()
            return CustomResponse(
                general_message=f'Dynamic Role of type {type} and role {role} deleted successfully'
                ).get_success_response()
        return CustomResponse(
            general_message=f'No such Dynamic Role of type {type} and role {role} present'
            ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        type = request.data['type']
        role = request.data['role']
        new_role = request.data['new_role']
        context = {'user_id': user_id, 'new_role': new_role}
        dynamic_role = DynamicRole.objects.filter(type=type, role__title=role).first()
        if dynamic_role is None:
            return CustomResponse(general_message='Dynamic Role does not exist').get_failure_response()
        serializer = DynamicRoleUpdateSerializer(dynamic_role, data={'type': type}, context=context)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Dynamic Role updated successfully', response=serializer.data).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()