from rest_framework.views import APIView
from utils.response import CustomResponse
from utils.types import CouponResponseKey, DiscountTypes
from db.user import UserCouponLink
from rest_framework.response import Response


class CouponApi(APIView):
    def post(self, request):
        if coupon_code := request.data.get("data"):
            if UserCouponLink.objects.filter(coupon=coupon_code).exists():
                data = {
                    CouponResponseKey.DISCOUNT_TYPE.value: DiscountTypes.PERCENTAGE.value,
                    CouponResponseKey.DISCOUNT_VALUE.value: 100,
                    CouponResponseKey.TICKET.value: ["bb3a795e-060d-4f6d-9bc7-107632589c35"],
                }
                return CustomResponse(
                    general_message="Coupon is valid", response=data
                ).get_success_response()
            return CustomResponse(general_message="Coupon is invalid").get_failure_response()
        return CustomResponse(general_message="Coupon code is required").get_failure_response()
