from rest_framework.views import APIView
from .serializers import PortalSerializer
from utils.utils_views import CustomResponse
from portal.models import Portal,PortalUserMailValidate
from user.models import Student
from decouple import config
from uuid import uuid4
from datetime import datetime, timedelta



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
        portal_token = request.headers.get('portalToken')
        portal = Portal.objects.filter(portal_token=portal_token).first()
        if portal is None:
            return CustomResponse({"hasError":True,"statusCode":400,"message":"Invalid Portal","response":{}}).get_failure_response() 
        name = request.data.get('name')
        mu_id = request.data.get('mu_id')
        user = Student.objects.get(mu_id=mu_id)  
        
        if user is None:
            return CustomResponse({"hasError":True,"statusCode":400,"message":"Invalid mu-id","response":{}}).get_failure_response()  
        if not name:
            return CustomResponse({"hasError":True,"statusCode":400,"message":"Invalid name","response":{}}).get_failure_response() 
        
        mail_token = uuid4()
        expiry_time = datetime.now() + timedelta(seconds=1800)
        PortalUserMailValidate.objects.create(portal_id=portal,user_id=user,token=mail_token,expiry=expiry_time)

        return CustomResponse({"hasError":False,"statusCode":200,"message":"Success","response":{"name":user.fullname,"muid":user.mu_id}}).get_success_response()
    
    


        
