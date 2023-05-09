from rest_framework.views import APIView
from db.task import InterestGroup
from utils.permission import CustomizePermission, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from .dash_ig_serializer import InterestGroupSerializer


class InterestGroupAPI(APIView):
    authentication_classes = [CustomizePermission] #for logged in users
    @RoleRequired(roles=[RoleType.ADMIN, ]) #for admin
    def get(self, request):
        ig_serializer = InterestGroup.objects.all()
        ig_serializer_data = InterestGroupSerializer(ig_serializer, many=True).data
        return CustomResponse(
            response={"interestGroups": ig_serializer_data}
        ).get_success_response()