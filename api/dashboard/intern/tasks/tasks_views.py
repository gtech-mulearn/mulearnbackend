from rest_framework.views import APIView

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.intern import InternTask
from .serializers import InternTaskSerializer

class InternTaskMineAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        tasks = InternTask.objects.filter(assigned_to_id=user_id).order_by('-created_at')
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            tasks, request,
            ['title', 'status', 'category'],
            {'created_at': 'created_at', 'status': 'status'}
        )
        
        serializer = InternTaskSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()
