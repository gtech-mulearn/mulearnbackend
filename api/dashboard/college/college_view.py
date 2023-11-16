from rest_framework.views import APIView

from db.organization import College, OrgDiscordLink
from utils.permission import JWTUtils
from utils.response import CustomResponse
from .serializer import (
    CollegeCreateDeleteSerializer,
    CollegeListSerializer,
    CollegeEditSerializer,
)
from django.db.models import Prefetch


class CollegeApi(APIView):
    def get(self, request, college_code=None):
        if college_code:
            colleges = College.objects.filter(id=college_code)
        else:
            colleges = College.objects.all()

        # College.objects.select_related("created_by", "updated_by", "org")
        # .prefetch_related(
        #     Prefetch(
        #         "org__org_discord_link_org_id",
        #         queryset=OrgDiscordLink.objects.all(),
        #     )
        # )
        # .all()

        # if college_code:
        #     colleges = colleges.filter(org__code=college_code)
        serializer = CollegeListSerializer(colleges, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = CollegeCreateDeleteSerializer(
            data=request.data, context={"user_id": user_id}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Level added successfully"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class CollegeUpdateDeleteApi(APIView):
    def delete(self, request, college_id):
        if college := College.objects.filter(id=college_id).first():
            CollegeCreateDeleteSerializer().destroy(college)
            return CustomResponse(
                general_message="College succesfully deleted"
            ).get_success_response()
        return CustomResponse(general_message="Invalid college").get_failure_response()

    def patch(self, request, college_id):
        user_id = JWTUtils.fetch_user_id(request)
        college = College.objects.filter(id=college_id).first()
        if college is None:
            return CustomResponse(
                general_message="Invalid college"
            ).get_failure_response()
        serializer = CollegeEditSerializer(
            college, data=request.data, context={"user_id": user_id}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Level updated successfully"
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()
