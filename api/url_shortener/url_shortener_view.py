from rest_framework.views import APIView

from api.url_shortener.serializers import (
    ShowShortenUrlsSerializer,
    ShortenUrlsCreateUpdateSerializer
)
from db.url_shortener import UrlShortener, UrlShortenerTracker
from utils.permission import CustomizePermission
from utils.permission import role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils


class UrlShortenerAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.ASSOCIATE.value]
    )
    def post(self, request):

        serializer = ShortenUrlsCreateUpdateSerializer(
            data=request.data,
            context={
                "request": request
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message="Url created successfully."
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.ASSOCIATE.value]
    )
    def get(self, request):
        url_shortener_objects = UrlShortener.objects.all()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            url_shortener_objects,
            request,
            [
                "title",
                "short_url",
                "long_url"
            ],
            {
                "title": "title",
                "created_at": "created_at"
            },
        )

        if len(url_shortener_objects) == 0:
            return CustomResponse(
                general_message="No URL related data available"
            ).get_failure_response()

        url_shortener_list = ShowShortenUrlsSerializer(
            paginated_queryset.get(
                "queryset"
            ),
            many=True
        ).data

        return CustomResponse().paginated_response(
            data=url_shortener_list,
            pagination=paginated_queryset.get("pagination")
        )

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.ASSOCIATE.value]
    )
    def put(self, request, url_id):
        url_shortener = UrlShortener.objects.filter(
            id=url_id
        ).first()

        if url_shortener is None:
            return CustomResponse(
                general_message="Invalid Url ID"
            ).get_failure_response()

        serializer = ShortenUrlsCreateUpdateSerializer(
            url_shortener,
            data=request.data,
            context={
                "request": request
            }
        )
        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message="Url Edited Successfully"
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.ASSOCIATE.value]
    )
    def delete(self, request, url_id):
        url_shortener_object = UrlShortener.objects.filter(
            id=url_id
        ).first()

        if url_shortener_object is None:
            return CustomResponse(
                general_message="invalid URL id"
            ).get_success_response()

        url_shortener_object.delete()
        return CustomResponse(
            general_message="Url deleted successfully.."
        ).get_success_response()


class UrlAnalyticsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.ASSOCIATE.value]
    )
    def get(self, request, url_id):
        queryset = UrlShortenerTracker.objects.filter(url_shortener__id=url_id)

        browsers = {}
        operating_systems = {}
        devices = {}
        referrer = {}

        if queryset.exists():  # Check if the queryset is not empty
            for query in queryset:
                # Counting browsers
                if browsers.get(query.browser):
                    browsers[query.browser] += 1
                else:
                    browsers[query.browser] = 1

                # Counting operating systems
                if operating_systems.get(query.operating_system):
                    operating_systems[query.operating_system] += 1
                else:
                    operating_systems[query.operating_system] = 1

                # Counting devices
                if devices.get(query.device_type):
                    devices[query.device_type] += 1
                else:
                    devices[query.device_type] = 1

                if referrer.get(query.referrer):
                    referrer[query.referrer] += 1
                else:
                    referrer[query.referrer] = 1

            total_clicks = queryset.first().url_shortener.count
        else:
            total_clicks = 0

        result = {
            'total_clicks': total_clicks,
            'browsers': browsers,
            'platforms': operating_systems,
            'devices': devices,
            'sources': referrer,
        }

        return CustomResponse(response=result).get_success_response()
