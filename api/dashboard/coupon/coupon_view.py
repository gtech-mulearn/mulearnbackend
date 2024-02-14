from rest_framework.views import APIView
from utils.response import CustomResponse
from db.user import UserCouponLink
from rest_framework.response import Response


class CouponApi(APIView):
    def post(self, request):
        if coupon_code := request.data.get('data'):
            if UserCouponLink.objects.filter(coupon=coupon_code).exists():
                return Response(data={"discount_type": "Percentage", "discount_value": 100})
            return Response(data={"discount_type": "Percentage", "discount_value": 0})
        return Response(data={"discount_type": "Percentage", "discount_value": 0})
