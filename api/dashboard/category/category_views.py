from db.task import Category
from rest_framework.views import APIView
from utils.permission import JWTUtils
from utils.response import CustomResponse
from .category_serializer import CategoryListSerializer, CategoryCUDSerializer

class CategoryAPI(APIView):
    def get(self, request, category_id=None):
        if category_id:
            category = Category.objects.filter(id=category_id).first()
            if not category:
                return CustomResponse(
                    general_message='Invalid Category id'
                ).get_failure_response()
            serializer = CategoryListSerializer(category)
            return CustomResponse(response=serializer.data).get_success_response()
        
        category = Category.objects.all()
        serializer = CategoryListSerializer(category, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = CategoryCUDSerializer(
            data=request.data,
            context={'user_id': user_id}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message='Category created successfully',
                response=serializer.data
            ).get_success_response()
        return CustomResponse(
            general_message=serializer.errors,
        ).get_failure_response()

    def put(self, request, category_id):
        user_id = JWTUtils.fetch_user_id(request)
        category = Category.objects.filter(id=category_id).first()
        if not category:
            return CustomResponse(
                general_message='Invalid Category id'
            ).get_failure_response()
        serializer = CategoryCUDSerializer(
            category,
            data=request.data,
            context={'user_id': user_id}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message='Category updated successfully',
                response=serializer.data
            ).get_success_response()
        return CustomResponse(
            general_message=serializer.errors,
        ).get_failure_response()

    def patch(self, request, category_id):
        user_id = JWTUtils.fetch_user_id(request)
        category = Category.objects.filter(id=category_id).first()
        if not category:
            return CustomResponse(
                general_message='Invalid Category id'
            ).get_failure_response()
        serializer = CategoryCUDSerializer(
            category,
            data=request.data,
            context={'user_id': user_id},
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message='Category updated successfully',
                response=serializer.data
            ).get_success_response()
        return CustomResponse(
            general_message=serializer.errors,
        ).get_failure_response()

    def delete(self, request, category_id):
        category = Category.objects.filter(id=category_id).first()
        if not category:
            return CustomResponse(
                general_message='Invalid Category id'
            ).get_failure_response()
        category.delete()
        return CustomResponse(
            general_message='Category deleted successfully'
        ).get_success_response()