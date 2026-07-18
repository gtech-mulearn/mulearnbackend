from django.db import transaction, IntegrityError
from django.db.models import F
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from db.comic import Comic, ComicLikeLink, ComicBookmarkLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse

from .serializers import ComicLikeSerializer, ComicBookmarkSerializer


class LikeComicAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=["Comic Reader"])
    def post(self, request, comic_id):
        # We pass comic_id into the serializer data for validation
        serializer = ComicLikeSerializer(
            data={'comic_id': comic_id},
            context={'request': request}
        )
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    serializer.save()
                    Comic.objects.filter(id=comic_id).update(like_count=F('like_count') + 1)
                return CustomResponse(response={"message": "Comic liked successfully"}).get_success_response()
            except IntegrityError:
                return CustomResponse(
                    general_message="Comic already liked."
                ).get_failure_response(status_code=409)
        
        return CustomResponse(
            general_message="Validation failed.",
            response=serializer.errors
        ).get_failure_response()

    @extend_schema(tags=["Comic Reader"])
    def delete(self, request, comic_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        with transaction.atomic():
            deleted, _ = ComicLikeLink.objects.filter(comic_id=comic_id, user_id=user_id).delete()
            if deleted > 0:
                Comic.objects.filter(id=comic_id).update(like_count=F('like_count') - 1)
                return CustomResponse(response={"message": "Comic unliked successfully"}).get_success_response()
            else:
                return CustomResponse(general_message="Comic like not found.").get_failure_response(status_code=404)


class BookmarkComicAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=["Comic Reader"])
    def post(self, request, comic_id):
        serializer = ComicBookmarkSerializer(
            data={'comic_id': comic_id},
            context={'request': request}
        )
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    serializer.save()
                    Comic.objects.filter(id=comic_id).update(bookmark_count=F('bookmark_count') + 1)
                return CustomResponse(response={"message": "Comic bookmarked successfully"}).get_success_response()
            except IntegrityError:
                return CustomResponse(
                    general_message="Comic already bookmarked."
                ).get_failure_response(status_code=409)
        
        return CustomResponse(
            general_message="Validation failed.",
            response=serializer.errors
        ).get_failure_response()

    @extend_schema(tags=["Comic Reader"])
    def delete(self, request, comic_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        with transaction.atomic():
            deleted, _ = ComicBookmarkLink.objects.filter(comic_id=comic_id, user_id=user_id).delete()
            if deleted > 0:
                Comic.objects.filter(id=comic_id).update(bookmark_count=F('bookmark_count') - 1)
                return CustomResponse(response={"message": "Comic bookmark removed successfully"}).get_success_response()
            else:
                return CustomResponse(general_message="Comic bookmark not found.").get_failure_response(status_code=404)


class InteractionStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=["Comic Reader"])
    def get(self, request, comic_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        is_liked = ComicLikeLink.objects.filter(comic_id=comic_id, user_id=user_id).exists()
        is_bookmarked = ComicBookmarkLink.objects.filter(comic_id=comic_id, user_id=user_id).exists()
        
        return CustomResponse(
            response={
                "is_liked": is_liked,
                "is_bookmarked": is_bookmarked
            }
        ).get_success_response()
