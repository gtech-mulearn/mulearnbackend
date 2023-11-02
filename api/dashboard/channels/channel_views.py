from rest_framework.views import APIView

from db.task import Channel
from utils.permission import CustomizePermission, JWTUtils
from utils.permission import role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from .serializers import ChannelCUDSerializer, ChannelListSerializer

class ChannelCRUDAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):

        channel = Channel.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            channel,
            request,
            ['id', 'name', 'discord_id']
        )

        serializer = ChannelListSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get(
                "pagination"
            )
        )

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        
        user_id = JWTUtils.fetch_user_id(request)

        serializer = ChannelCUDSerializer(
            data=request.data,
            context={
                "user_id": user_id,
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{request.data.get('name')} Channel created successfully",
                response=serializer.data
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors,
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def put(self, request, channel_id):

        user_id = JWTUtils.fetch_user_id(request)

        channel = Channel.objects.filter(
            id=channel_id
        ).first()

        if channel is None:
            return CustomResponse(
                general_message="Invalid channels id"
            ).get_failure_response()

        serializer = ChannelCUDSerializer(
            channel,
            data=request.data,
            context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{channel.name} Edited Successfully"
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, channel_id):

        channel = Channel.objects.filter(
            id=channel_id
        ).first()

        if channel is None:
            return CustomResponse(
                general_message="Invalid channels id"
            ).get_failure_response()

        channel.delete()

        return CustomResponse(
            general_message=f"{channel.name} Deleted Successfully"
        ).get_success_response()