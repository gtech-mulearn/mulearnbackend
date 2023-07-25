from rest_framework.views import APIView
from db.learning_circle import LearningCircle, UserCircleLink
from db.organization import UserOrganizationLink
from utils.permission import JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from .dash_lc_serializer import LearningCircleSerializer, LearningCircleCreateSerializer, LearningCircleHomeSerializer, \
    LearningCircleUpdateSerializer, LearningCircleJoinSerializer , LearningCircleMeetSerializer


class LearningCircleAPI(APIView):
    def get(self, request):  # lists the learning circle in the user's college
        user_id = JWTUtils.fetch_user_id(request)
        org_id = UserOrganizationLink.objects.filter(user_id=user_id,
                                                     org__org_type=OrganizationType.COLLEGE.value).values_list('org_id',
                                                                                                               flat=True).first()
        learning_queryset = LearningCircle.objects.filter(org=org_id)
        learning_serializer = LearningCircleSerializer(learning_queryset, many=True)
        return CustomResponse(response=learning_serializer.data).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        # COLLEGE_CODE+FIRST_TWO_LETTES_OF_LEARNING_CIRCLE+INTEREST_GROUP
        serializer = LearningCircleCreateSerializer(data=request.data, context={'user_id': user_id})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='LearningCircle created successfully').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class LearningCircleJoinApi(APIView):
    def post(self, request, circle_id):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = LearningCircleJoinSerializer(data=request.data,
                                                  context={'user_id': user_id, 'circle_id': circle_id})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Request sent').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class LearningCircleListApi(APIView):
    def get(self, request):  # Lists user's learning circle
        user_id = JWTUtils.fetch_user_id(request)
        learning_queryset = LearningCircle.objects.filter(usercirclelink__user_id=user_id)
        learning_serializer = LearningCircleSerializer(learning_queryset, many=True)
        return CustomResponse(response=learning_serializer.data).get_success_response()

class LearningCircleMeetAPI(APIView):
    def patch(self,request,circle_id):
        learning_circle = LearningCircle.objects.filter(id=circle_id).first()
        serializer = LearningCircleMeetSerializer(learning_circle,data=request.data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Meet updated successfully').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

class LearningCircleHomeApi(APIView):
    def get(self, request, circle_id):
        user_id = JWTUtils.fetch_user_id(request)
        learning_circle = LearningCircle.objects.filter(id=circle_id).first()
        serializer = LearningCircleHomeSerializer(learning_circle, many=False, context={"user_id": user_id})
        return CustomResponse(response=serializer.data).get_success_response()

    def patch(self, request, member_id, circle_id):
        user_id = JWTUtils.fetch_user_id(request)
        learning_circle_link = UserCircleLink.objects.filter(user_id=member_id, circle_id=circle_id).first()
        serializer = LearningCircleUpdateSerializer(learning_circle_link, data=request.data,
                                                    context={'user_id': user_id})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Approved successfully').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()
