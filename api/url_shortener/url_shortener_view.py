import re
import uuid

from rest_framework.views import APIView

from api.url_shortener.serializers import ShowShortenUrlsSerializer
from db.url_shortener import UrlShortener
from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.permission import role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import DateTimeUtils, CommonUtils


class UrlShortenerAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def post(self, request):

        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()

        special_characters_list = r'[~`!@#$%^&*()-+=|{}[\]:;"\'<>,?\\]'
        long_url = request.data.get('longUrl')
        short_url = request.data.get('shortUrl')
        title = request.data.get('title')

        long_url_data = UrlShortener.objects.filter(long_url=long_url).first()
        if long_url_data:
            return CustomResponse(general_message='Long url already exist').get_failure_response()

        short_url_data = UrlShortener.objects.filter(short_url=short_url).first()
        if short_url_data:
            return CustomResponse(general_message='Short url already exist').get_failure_response()

        special_character = re.search(special_characters_list, short_url)

        if special_character or len(short_url) > 300:

            return CustomResponse(general_message='Your shortened URL should be less than 300 characters in length.'
                                                  'only include letters, numbers and following special characters (/_)'
                                  ).get_failure_response()
        else:
            UrlShortener.objects.create(id=uuid.uuid4(), short_url=short_url, long_url=long_url,
                                        title=title,
                                        updated_by=user,
                                        updated_at=DateTimeUtils.get_current_utc_time(),
                                        created_by=user,
                                        created_at=DateTimeUtils.get_current_utc_time())
            return CustomResponse(general_message='Url created successfully.').get_success_response()

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request):
        url_shortener_objects = UrlShortener.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(url_shortener_objects, request, ['title'])

        if len(url_shortener_objects) == 0:
            return CustomResponse(general_message='No URL related data available').get_failure_response()

        url_shortener_list = ShowShortenUrlsSerializer(paginated_queryset.get('queryset'), many=True).data

        return CustomResponse().paginated_response(data=url_shortener_list,
                                                   pagination=paginated_queryset.get('pagination'))

    @role_required([RoleType.ADMIN.value, ])
    def put(self, request, url_id):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()

        special_characters_list = r'[~`!@#$%^&*()-+=|{}[\]:;"\'<>,?\\]'

        short_url_new = request.data.get('shortUrlNew')

        url_shortener_object = UrlShortener.objects.filter(id=url_id).first()
        if url_shortener_object is None:
            return CustomResponse(general_message='Invalid URL Id').get_failure_response()

        if short_url_new == url_shortener_object.short_url:
            return CustomResponse(general_message='current URL matched with old URL').get_failure_response()

        url_shortener_object_new = UrlShortener.objects.filter(short_url=short_url_new).first()
        if url_shortener_object_new:
            return CustomResponse(general_message='URL already used').get_failure_response()

        special_character = re.search(special_characters_list, short_url_new)

        if special_character or len(short_url_new) > 300:
            return CustomResponse(general_message='Your shortened URL should be less than 300 characters in length.'
                                                  'only include letters, numbers and following special characters (/_)'
                                  ).get_failure_response()

        url_shortener_object.short_url = short_url_new
        url_shortener_object.updated_by = user
        url_shortener_object.updated_at = DateTimeUtils.get_current_utc_time()

        url_shortener_object.save()

        return CustomResponse(general_message='Url changed successfully').get_success_response()

    @role_required([RoleType.ADMIN.value, ])
    def delete(self, request, url_id):
        url_shortener_object = UrlShortener.objects.filter(id=url_id).first()
        if url_shortener_object is None:
            return CustomResponse(general_message='invalid URL id').get_success_response()

        url_shortener_object.delete()
        return CustomResponse(general_message='Url deleted successfully..').get_success_response()
