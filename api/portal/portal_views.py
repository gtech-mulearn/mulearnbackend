from rest_framework.views import APIView
from .serializers import PortalSerializer
from utils.utils_views import CustomResponse
from portal.models import*
from user.models import Student
from decouple import config


# class AddPortal(APIView):
#     def post(self, request):
#         print(request)
#         serializer = PortalSerializer(data=request.data)
#         if serializer.is_valid():
#             obj = serializer.save()
#             return CustomResponse(response={"access_id": obj.access_id}).get_success_response()
#         else:
#             return CustomResponse(has_error=True, status_code=400, message=serializer.errors).get_failure_response()

class MuidValidate(APIView):
    def post(self, request):
        secretToken = request.headers.get('secretToken')
        print(secretToken)
        if secretToken == config('SECRET_KEY'):
            name = request.data.get('name')
            mu_id = request.data.get('mu_id')
            user = Student.objects.get(mu_id=mu_id)        
            return CustomResponse({"hasError":False,"statusCode":200,"message":"User Validated","response":{"name":user.fullname,"muId":user.mu_id}}).get_success_response()
        else:
            return CustomResponse({"hasError":True,"statusCode":404,"message":"Validation Falied","response":{}}).get_failure_response()
