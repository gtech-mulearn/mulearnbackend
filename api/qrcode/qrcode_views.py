from rest_framework.views import APIView
from io import BytesIO
import qrcode
from utils.permission import JWTUtils,role_required,CustomizePermission
from utils.types import RoleType
from db.user import User
from PIL import Image
from django.http import HttpResponse
import decouple

class QrcodeManagmentAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        print(request)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        base_url = decouple.config("FR_DOMAIN_NAME")
        user_muid =JWTUtils.fetch_muid(request)
        data = base_url+"/profile/"+user_muid
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer)
        buffer.seek(0)

        return HttpResponse(buffer, content_type="image/png")
