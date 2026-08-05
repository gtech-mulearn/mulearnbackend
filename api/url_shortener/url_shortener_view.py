from rest_framework.views import APIView

from api.url_shortener.serializers import (
    ShowShortenUrlsSerializer,
    ShortenUrlsCreateUpdateSerializer
)
from db.url_shortener import UrlShortener, UrlShortenerTracker
from utils.permission import CustomizePermission
from utils.permission import role_required
from utils.types import RoleType
from utils.response import CustomResponse
from utils.utils import CommonUtils
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s


class UrlShortenerAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.ASSOCIATE.value]
    )
    @extend_schema(
        tags=['Url Shortener'],
        description="Create Url Shortener.",
        request=ShortenUrlsCreateUpdateSerializer,
        responses={200: ShortenUrlsCreateUpdateSerializer},
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
    @extend_schema(
        tags=['Url Shortener'],
        description="Retrieve Url Shortener.",
        responses={200: ShowShortenUrlsSerializer},
    )
    def get(self, request):
        url_shortener_objects = UrlShortener.objects.select_related(
            "created_by", "updated_by"
        ).order_by('-created_at')

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
    @extend_schema(
        tags=['Url Shortener'],
        description="Update Url Shortener.",
        responses={200: ShortenUrlsCreateUpdateSerializer},
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
    @extend_schema(tags=['Url Shortener'], description="Delete Url Shortener.",
        responses={200: ShortenUrlsCreateUpdateSerializer},
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
    @extend_schema(tags=['Url Shortener'], description="Retrieve Url Analytics.",
        responses={200: inline_serializer(
            name='UrlShortenerAnalyticsResponse',
            fields={
                'total_clicks': s.IntegerField(),
                'created_on': s.CharField(),
                'browsers': s.JSONField(),
                'platforms': s.JSONField(),
                'devices': s.JSONField(),
                'sources': s.JSONField(),
                'ip_address': s.JSONField(),
                'city': s.JSONField(),
                'region': s.JSONField(),
                'countries': s.JSONField(),
                'time_based_data': s.JSONField(),
                'long_url': s.CharField(),
                'short_url': s.CharField(),
                'title': s.CharField(),
                'created_by': s.CharField(),
                'updated_by': s.CharField(),
                'updated_at': s.CharField(),
            },
        )},
    )
    def get(self, request, url_id):
        queryset = UrlShortenerTracker.objects.filter(url_shortener__id=url_id)
        # long and short url
        url_shortener = UrlShortener.objects.filter(id=url_id).first()

        if not url_shortener:
            # The short URL itself does not exist — this is a genuine 404.
            return CustomResponse(
                general_message="Short URL not found"
            ).get_failure_response(status_code=404)

        if not queryset.exists():
            # The URL exists but has not been clicked yet. This is a valid empty
            # state, not an error, so return a 200 with zero-value analytics.
            # The client renders zeros instead of a failure screen.
            empty_result = {
                'total_clicks': 0,
                'created_on': url_shortener.created_at.strftime('%Y-%m-%d')
                if getattr(url_shortener, 'created_at', None) else None,
                'browsers': {},
                'platforms': {},
                'devices': {},
                'sources': {},
                'ip_address': {},
                'city': {},
                'region': {},
                'countries': {},
                'time_based_data': {'all_time': []},
                'long_url': url_shortener.long_url,
                'short_url': url_shortener.short_url,
                'title': url_shortener.title,
                'created_by': getattr(url_shortener.created_by, 'full_name', None),
                'updated_by': getattr(url_shortener.updated_by, 'full_name', None),
                'updated_at': url_shortener.updated_at.strftime('%Y-%m-%d')
                if getattr(url_shortener, 'updated_at', None) else None,
            }
            return CustomResponse(response=empty_result).get_success_response()

        browsers = {}
        platforms = {}
        devices = {}
        sources = {}
        countries = {}
        ip_address = {}
        city = {}
        region = {}
        time_based_data = {'all_time': []}

        for query in queryset:
            # Counting browsers, platforms, devices, sources, countries, and dimensions
            browsers[query.browser] = browsers.get(query.browser, 0) + 1
            platforms[query.operating_system] = platforms.get(
                query.operating_system, 0) + 1
            devices[query.device_type] = devices.get(
                query.device_type, 0) + 1
            sources[query.referrer] = sources.get(query.referrer, 0) + 1
            countries[query.country] = countries.get(query.country, 0) + 1
            ip_address[query.ip_address] = ip_address.get(
                query.ip_address, 0) + 1
            city[query.city] = city.get(query.city, 0) + 1
            region[query.region] = region.get(query.region, 0) + 1

            # Create a list of time-based data
            time_based_data['all_time'].append([
                query.created_at.strftime(
                    '%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                1  # Assuming each record contributes 1 click
            ])

        result = {
            'total_clicks': queryset.count(),
            'created_on': queryset.first().created_at.strftime('%Y-%m-%d'),
            'browsers': browsers,
            'platforms': platforms,
            'devices': devices,
            'sources': sources,
            'ip_address': ip_address,
            'city': city,
            'region': region,
            'countries': countries,
            'time_based_data': time_based_data,
            'long_url': url_shortener.long_url,
            'short_url': url_shortener.short_url,
            'title': url_shortener.title,
            'created_by': getattr(url_shortener.created_by, 'full_name', None),
            'updated_by': getattr(url_shortener.updated_by, 'full_name', None),
            'updated_at': url_shortener.updated_at.strftime('%Y-%m-%d')
            if getattr(url_shortener, 'updated_at', None) else None,
        }

        return CustomResponse(response=result).get_success_response()
