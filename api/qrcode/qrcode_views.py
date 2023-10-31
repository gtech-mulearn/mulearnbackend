import qrcode
import decouple
from PIL import Image
from io import BytesIO
from db.user import User
from utils.types import RoleType
from django.http import HttpResponse
from rest_framework.views import APIView
from utils.permission import JWTUtils,role_required,CustomizePermission

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

        #  files = {'file': buffer}
        # upload_url = 'YOUR_IMAGE_SERVER_API_ENDPOINT'  # Replace with your server's endpoint
        # response = requests.post(upload_url, files=files)

        # if response.status_code == 200:
        #     # Image uploaded successfully
        #     return HttpResponse("Image uploaded to server")
        # else:
        #     # Failed to upload image
        #     return HttpResponse("Failed to upload image", status=500)

        img.save('path/to/your/local/directory/qr_code_image.png')  # Replace 'path/to/your/local/directory/' with the actual directory path

        # Return a success message or any response you prefer
        return HttpResponse("QR code image saved locally")






