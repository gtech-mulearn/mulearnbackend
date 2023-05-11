import uuid
from rest_framework.views import APIView
from db.task import InterestGroup
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import DateTimeUtils
from .dash_ig_serializer import InterestGroupSerializer


class InterestGroupAPI(APIView):
    
    #GET Request to show all interest groups
    authentication_classes = [CustomizePermission] #for logged in users
    @RoleRequired(roles=[RoleType.ADMIN, ]) #for admin
    def get(self, request):
        ig_serializer = InterestGroup.objects.all()
        ig_serializer_data = InterestGroupSerializer(ig_serializer, many=True).data
        return CustomResponse(
            response={"interestGroups": ig_serializer_data}
        ).get_success_response()

	#POST Request to create a new interest group
    authentication_classes = [CustomizePermission]
    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        ig_data = InterestGroup.objects.create(
            id = uuid.uuid4(),
			name = request.POST["name"],
			updated_by=user,
			updated_at=DateTimeUtils.get_current_utc_time(),
			created_by=user,
			created_at=DateTimeUtils.get_current_utc_time()
		)
        serializer = InterestGroupSerializer(ig_data)
        return CustomResponse(
            response={"interestGroup": serializer}
        ).get_success_response()
    
    #POST Request to edit/delete an InterestGroup. Use endpoint + /<id>/
    authentication_classes = [CustomizePermission]
    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request, pk):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        igData = InterestGroup.objects.get(id=pk)
        
        #body should contain 'delete': '1' for delete
        if (request.POST["delete"] == '1') :
            igData.delete()
            
        #body should contain 'name': '<new name of interst group>' for edit
        else :
            igData.name	= request.POST["name"],
            igData.updated_by = user,
            igData.updated_at = DateTimeUtils.get_current_utc_time(),
            igData.save()
        serializer = InterestGroupSerializer(igData)
        return CustomResponse(
            response={"interestGroup": serializer}
        ).get_success_response()
