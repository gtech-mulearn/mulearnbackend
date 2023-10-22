from rest_framework.views import APIView
from utils.permission import CustomizePermission,role_required,JWTUtils
from utils.types import RoleType
from .serializers import ChannelReadSerializer,ChannelCreateUpdateSerializer
from db.task import Channel
from utils.response import CustomResponse

class ChannelGetView(APIView):
  authentication_classes = [CustomizePermission]


  def get(self,request):
    all_channels = Channel.objects.all()

    serial_ = ChannelReadSerializer(data=all_channels,many=True)
    serial_.is_valid()
    return CustomResponse(response=serial_.data).get_success_response()

class ChannelAddView(APIView):
  authentication_classes = [CustomizePermission]

  @role_required([RoleType.ADMIN.value])
  def post(self,request):
    user_id = JWTUtils.fetch_user_id(request)
    
    serial_ = ChannelCreateUpdateSerializer(data=request.data,context={'user_id':user_id})

    if serial_.is_valid():
        serial_.save()

        return CustomResponse(
            general_message=f"{request.data.get('name')} added successfully"
        ).get_success_response()

    return CustomResponse(
        general_message=serial_.errors
    ).get_failure_response()


class ChannelEditView(APIView):
  authentication_classes = [CustomizePermission]

  @role_required([RoleType.ADMIN.value])
  def put(self,request,channel_id):
    user_id = JWTUtils.fetch_user_id(request)
    channel = Channel.objects.filter(id=channel_id).first()

    if channel is None:
            return CustomResponse(
                general_message="Invalid channel"
            ).get_failure_response()

    serializer = ChannelCreateUpdateSerializer(
        channel,
        data=request.data,
        context={
            "user_id": user_id
        }
    )
    if serializer.is_valid():
      serializer.save()

      return CustomResponse(
          general_message=f"{channel.name} Edited Successfully"
      ).get_success_response()

    return CustomResponse(
        message=serializer.errors
    ).get_failure_response()

class ChannelDeleteView(APIView):
  authentication_classes = [CustomizePermission]

  @role_required([RoleType.ADMIN.value])
  def delete(self,request,channel_id):
    user_id = JWTUtils.fetch_user_id(request)
    channel = Channel.objects.filter(id=channel_id).first()

    if channel is None:
            return CustomResponse(
                general_message="Invalid channel"
            ).get_failure_response()
    channel.delete()
    return CustomResponse(
          general_message=f"{channel.name} Deleted Successfully"
      ).get_success_response()