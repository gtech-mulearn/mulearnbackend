from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from db.user import UserCouponLink
from utils.response import CustomResponse
from utils.types import CouponResponseKey, DiscountTypes


class CouponApi(APIView):
    def post(self, request):
        if not (coupon_code := request.data.get("code")):
            return CustomResponse(general_message="Coupon code is required").get_failure_response()

        if not UserCouponLink.objects.filter(coupon=coupon_code).exists():
            return CustomResponse(general_message="Coupon is invalid").get_failure_response()

        return Response({
            CouponResponseKey.DISCOUNT_TYPE.value: DiscountTypes.PERCENTAGE.value,
            CouponResponseKey.DISCOUNT_VALUE.value: 100,
            CouponResponseKey.TICKET.value: ["bb3a795e-060d-4f6d-9bc7-107632589c35"],
        }, status=status.HTTP_200_OK)
