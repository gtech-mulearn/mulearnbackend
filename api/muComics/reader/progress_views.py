from rest_framework.views import APIView

from db.comic import ComicReadingProgress
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse

from .serializers import ComicReadingProgressSerializer


class ReadingProgressAPI(APIView):
    authentication_classes = [CustomizePermission]

    def put(self, request, comic_id):
        data = request.data.copy()
        data['comic_id'] = comic_id
        
        serializer = ComicReadingProgressSerializer(
            data=data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            progress = serializer.save()
            return CustomResponse(
                response={
                    "id": progress.id,
                    "comic_id": progress.comic_id,
                    "last_chapter_id": progress.last_chapter_id,
                    "last_page_number": progress.last_page_number,
                    "updated_at": progress.updated_at
                },
                general_message="Reading progress saved successfully"
            ).get_success_response()
            
        return CustomResponse(
            general_message="Validation failed.",
            response=serializer.errors
        ).get_failure_response()

    def get(self, request, comic_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        progress = ComicReadingProgress.objects.filter(
            comic_id=comic_id,
            user_id=user_id
        ).first()
        
        if progress:
            response_data = {
                "id": progress.id,
                "comic_id": progress.comic_id,
                "last_chapter_id": progress.last_chapter_id,
                "last_page_number": progress.last_page_number,
                "updated_at": progress.updated_at
            }
        else:
            response_data = None
            
        return CustomResponse(
            response=response_data
        ).get_success_response()
