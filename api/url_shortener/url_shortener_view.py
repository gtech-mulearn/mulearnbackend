from rest_framework.views import APIView
from utils.response import CustomResponse
from db.url_shortener import UrlShortener
from utils.utils_views import get_current_utc_time

import re
import uuid


class CreateShortenUrl(APIView):

    def get(self, request):

        special_characters_list = r'[~`!@#$%^&*()-+=|{}[\]:;"\'<>,.?\\]'

        long_url = request.data.get('long_url')
        short_url = request.data.get('short_url')

        long_url_data = UrlShortener.objects.filter(long_url=long_url).first()
        if long_url_data:
            return CustomResponse(general_message=['Long url already exist']).get_failure_response()

        short_url_data = UrlShortener.objects.filter(short_url=short_url).first()
        if short_url_data:
            return CustomResponse(general_message=['Short url already exist']).get_failure_response()

        special_character = re.search(special_characters_list, short_url)

        if special_character or len(short_url) > 300:

            return CustomResponse(general_message=['Your shortened URL should be less than 300 characters in length.',
                                                   'only include letters, numbers and following special characters (/_)']
                                  ).get_failure_response()
        else:

            url_shortener_table = UrlShortener.objects.create(id=uuid.uuid4(), short_url=short_url, long_url=long_url)
            return CustomResponse(general_message=['Url created successfully.']).get_success_response()


class ShowShortenUrls(APIView):

    def post(self, request):

        shorten_url_list = []
        url_shortener_objects = UrlShortener.objects.all()

        if len(url_shortener_objects) == 0:
            return CustomResponse(general_message=['No URL related data available']).get_failure_response()

        for url_shortener_object in url_shortener_objects:

            long_url = url_shortener_object.long_url
            short_url = url_shortener_object.short_url

            shorten_url_dict = {'long_url': long_url, 'short_url': short_url}
            shorten_url_list.append(shorten_url_dict)

        return CustomResponse(response=shorten_url_list).get_success_response()


class DeleteShortenUrl(APIView):

    def get(self, request):

        url_id = request.data.get('url_id')

        url_shortener_object = UrlShortener.objects.filter(id=url_id).first()
        if url_shortener_object is None:
            return CustomResponse(general_message=['invalid URL id']).get_success_response()

        url_shortener_object.delete()
        return CustomResponse(general_message=['Url deleted successfully..']).get_success_response()


class EditShortenUrl(APIView):

    def get(self, request):

        special_characters_list = r'[~`!@#$%^&*()-+=|{}[\]:;"\'<>,.?\\]'

        url_id = request.data.get('url_id')
        short_url_new = request.data.get('short_url_new')

        url_shortener_object = UrlShortener.objects.filter(id=url_id).first()
        if url_shortener_object is None:
            return CustomResponse(general_message=['Invalid URL Id']).get_failure_response()

        if short_url_new == url_shortener_object.short_url:
            return CustomResponse(general_message=['current URL matched with old URL']).get_failure_response()

        url_shortener_object_new = UrlShortener.objects.filter(short_url=short_url_new).first()
        if url_shortener_object_new:
            return CustomResponse(general_message=['URL already used']).get_failure_response()

        special_character = re.search(special_characters_list, short_url_new)

        if special_character or len(short_url_new) > 300:

            return CustomResponse(general_message=['Your shortened URL should be less than 300 characters in length.',
                                                   'only include letters, numbers and following special characters (/_)']
                                  ).get_failure_response()

        url_shortener_object.short_url = short_url_new
        url_shortener_object.updated_at = get_current_utc_time()

        url_shortener_object.save()

        return CustomResponse(general_message=['Url changed successfully']).get_success_response()
