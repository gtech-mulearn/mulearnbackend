from rest_framework.views import APIView
from .serializers import PortalSerializer
from utils.utils_views import CustomResponse
from user.models import Student,TotalKarma
import decouple


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
        screatToken = request.headers.get("secretToken")
        if screatToken == decouple.config("SECRET_KEY"):
            mu_id = request.data.get("mu_id")
            student = Student.objects.get(mu_id=mu_id)
            karma = TotalKarma.objects.get(user_id=student.user_id)
            return CustomResponse(response={"muid": mu_id, "fullname": student.fullname, "email": student.email, "karma": karma.karma}).get_success_response()
        else:
            return CustomResponse(has_error=True, status_code=400, message="token is incorrect").get_failure_response()