from rest_framework.views import APIView

from db.user import DynamicRole, Role, DynamicUser
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from .dynamic_management_serializer import DynamicRoleCreateSerializer, DynamicRoleListSerializer, DynamicRoleUpdateSerializer, DynamicTypeDropDownSerializer, RoleDropDownSerializer
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
    def delete(self, request, type_id): # delete
        if dynamic_role := DynamicRole.objects.filter(id=type_id).first():
            DynamicRoleUpdateSerializer().destroy(dynamic_role)
            return CustomResponse(
                general_message=f'Dynamic Role successfully deleted'
                ).get_success_response()
        return CustomResponse(
            general_message=f'Invalid Dynamic Role'
            ).get_failure_response()
    
    @role_required([RoleType.ADMIN.value])
    def patch(self, request, type_id):
        user_id = JWTUtils.fetch_user_id(request)
        context = {'user_id': user_id}
        dynamic_role = DynamicRole.objects.filter(id=type_id).first()
        serializer = DynamicRoleUpdateSerializer(dynamic_role, data=request.data, context=context)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Dynamic Role updated successfully').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()
    

class DynamicTypeDropDownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        dynamic_types = DynamicRole.objects.values('type').distinct()
        serializer = DynamicTypeDropDownSerializer(dynamic_types, many=True)
        return CustomResponse(response=serializer.data).get_success_response() 
    
class RoleDropDownAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        roles = Role.objects.all()
        serializer = RoleDropDownSerializer(roles, many=True)
        return CustomResponse(response=serializer.data).get_success_response()