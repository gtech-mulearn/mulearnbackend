from rest_framework.views import APIView
from db.learning_circle import LearningCircle, UserCircleLink
from db.organization import UserOrganizationLink
from utils.permission import JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from .dash_lc_serializer import LearningCircleSerializer, LearningCircleCreateSerializer, LearningCircleHomeSerializer, \
    LearningCircleUpdateSerializer, LearningCircleJoinSerializer, LearningCircleMeetSerializer, \
    LearningCircleMainSerializer, LearningCircleNoteSerializer


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
        serializer = LearningCircleCreateSerializer(data=request.data, context={'user_id': user_id})
        if serializer.is_valid():
            circle = serializer.save()
            return CustomResponse(general_message='LearningCircle created successfully',
                                  response={'circle_id': circle.id}).get_success_response()
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
    def patch(self, request, circle_id):
        learning_circle = LearningCircle.objects.filter(id=circle_id).first()
        serializer = LearningCircleMeetSerializer(learning_circle, data=request.data)
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

    def put(self, request, circle_id):
        learning_circle = LearningCircle.objects.filter(id=circle_id).first()
        serializer = LearningCircleNoteSerializer(learning_circle, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Note updated successfully').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class LearningCircleMainApi(APIView):
    def post(self, request):
        all_circles = LearningCircle.objects.all()
        ig_id = request.data.get('ig_id')
        org_id = request.data.get('org_id')
        district_id = request.data.get('district_id')

        if district_id:
            all_circles = all_circles.filter(org__district_id=district_id)

        if org_id:
            all_circles = all_circles.filter(org_id=org_id)

        if ig_id:
            all_circles = all_circles.filter(ig_id=ig_id)

        if ig_id or org_id or district_id:
            serializer = LearningCircleMainSerializer(all_circles, many=True)
        else:
            random_circles = all_circles.order_by('?')[:9]
            serializer = LearningCircleMainSerializer(random_circles, many=True)
        return CustomResponse(response=serializer.data).get_success_response()
