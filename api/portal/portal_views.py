from rest_framework.views import APIView
from .serializers import PortalSerializer
from utils.utils_views import CustomResponse
from user.models import Student, TotalKarma
import decouple
from portal.models import Portal, PortalUserAuth


# class AddPortal(APIView):
#     def post(self, request):
#         print(request)
#         serializer = PortalSerializer(data=request.data)
#         if serializer.is_valid():
#             obj = serializer.save()
#             return CustomResponse(response={"access_id": obj.access_id}).get_success_response()
#         else:
#             return CustomResponse(has_error=True, status_code=400, message=serializer.errors).get_failure_response()


class GetKarma(APIView):
    def get(self, request):
        portal_token = request.headers.get("portalToken")
        portal = Portal.objects.filter(portal_token=portal_token).first()
        if portal is None:
            return CustomResponse({"hasError": True, "statusCode": 400, "message": "Invalid Portal", "response": {}}).get_failure_response()
        mu_id = request.data.get("mu_id")
        student = Student.objects.filter(mu_id=mu_id).first()
        authorized_user = PortalUserAuth.objects.filter(user_id=student.user_id).first()
        if authorized_user and authorized_user.is_authenticated:
            karma = TotalKarma.objects.get(user_id=student.user_id)
            return CustomResponse(response={"muid": mu_id, "fullname": student.fullname, "email": student.email, "karma": karma.karma}).get_success_response()
        else:
            return CustomResponse(has_error=True, status_code=400, message="user not authorized to this portal").get_failure_response()
