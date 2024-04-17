from rest_framework.views import APIView
from utils.response import CustomResponse
from db.user import UserCouponLink
from rest_framework.response import Response





class CouponApi(APIView):
    def post(self, request):
        if coupon_code := request.data.get('data'):
            if UserCouponLink.objects.filter(coupon=coupon_code).exists():

                return CustomResponse(general_message="Coupon is valid").get_success_response()
            return CustomResponse(general_message="Coupon is invalid").get_failure_response()
        return CustomResponse(general_message="Coupon code is required").get_failure_response()

