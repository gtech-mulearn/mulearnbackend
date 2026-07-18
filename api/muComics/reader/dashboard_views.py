from rest_framework.views import APIView
from django.db.models import Q

from db.comic import ComicLikeLink, ComicBookmarkLink, ComicReadingProgress
from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils

from api.muComics.comic.serializers import MinimalUserSerializer
from .serializers import PaginatedBookmarkSerializer, PaginatedProgressSerializer


class ReaderDashboardAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(general_message="User not found").get_failure_response(status_code=404)
            
        stats = {
            "total_likes": ComicLikeLink.objects.filter(user_id=user_id).count(),
            "total_bookmarks": ComicBookmarkLink.objects.filter(user_id=user_id).count(),
            "in_progress": ComicReadingProgress.objects.filter(user_id=user_id).count()
        }
        
        return CustomResponse(
            response={
                "user": MinimalUserSerializer(user).data,
                "stats": stats
            }
        ).get_success_response()


class MyBookmarksAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        queryset = ComicBookmarkLink.objects.filter(
            user_id=user_id, 
            comic__deleted_at__isnull=True
        ).select_related('comic').order_by('-created_at')
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            queryset, 
            request, 
            search_fields=["comic__title", "comic__slug"]
        )
        
        serializer = PaginatedBookmarkSerializer(
            paginated_queryset.get("queryset"), 
            many=True,
            context={'request': request}
        )
        
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get("pagination")
        )


class MyReadingProgressAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        queryset = ComicReadingProgress.objects.filter(
            user_id=user_id, 
            comic__deleted_at__isnull=True
        ).select_related('comic', 'last_chapter').order_by('-updated_at')
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            queryset, 
            request, 
            search_fields=["comic__title", "comic__slug"]
        )
        
        serializer = PaginatedProgressSerializer(
            paginated_queryset.get("queryset"), 
            many=True,
            context={'request': request}
        )
        
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get("pagination")
        )
