from rest_framework.views import APIView
from utils.response import CustomResponse
from db.task import UnifiedEvent
from utils.permission import CustomizePermission, JWTUtils
from utils.utils import CommonUtils
from django.db.models import Q
from .serializers import UnifiedEventSerializer

class UnifiedEventAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request, event_id=None):
        if event_id:
            try:
                event = UnifiedEvent.objects.get(id=event_id)
                serializer = UnifiedEventSerializer(event)
                return CustomResponse(response=serializer.data).get_success_response()
            except UnifiedEvent.DoesNotExist:
                return CustomResponse(general_message="Event not found").get_failure_response()

        queryset = UnifiedEvent.objects.all()
        
        event_type = request.query_params.get('type')
        if event_type:
            queryset = queryset.filter(type=event_type)
            
        ig_id = request.query_params.get('ig')
        if ig_id:
            queryset = queryset.filter(ig_id=ig_id)
            
        campus_id = request.query_params.get('campus')
        if campus_id:
            queryset = queryset.filter(campus_id=campus_id)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            queryset, request,
            search_fields=["title", "description", "location"],
            sort_fields={"title": "title", "date": "date", "created_at": "created_at"}
        )

        serializer = UnifiedEventSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = UnifiedEventSerializer(data=request.data, context={'user_id': user_id})
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()

    def patch(self, request, event_id):
        try:
            event = UnifiedEvent.objects.get(id=event_id)
        except UnifiedEvent.DoesNotExist:
            return CustomResponse(general_message="Event not found").get_failure_response()

        serializer = UnifiedEventSerializer(event, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()

    def delete(self, request, event_id):
        try:
            event = UnifiedEvent.objects.get(id=event_id)
            event.delete()
            return CustomResponse(general_message="Event deleted successfully").get_success_response()
        except UnifiedEvent.DoesNotExist:
            return CustomResponse(general_message="Event not found").get_failure_response()
