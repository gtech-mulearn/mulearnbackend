from rest_framework.views import APIView

from api.url_shortener.serializers import (
    ShowShortenUrlsSerializer,
    ShortenUrlsCreateUpdateSerializer,
    ShowShortenUrlsTrackerSerializer
)
from db.url_shortener import UrlShortener, UrlShortenerTracker
from utils.permission import CustomizePermission
from utils.permission import role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from django.db.models import Count


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
        url_tracker_obj = UrlShortener.objects.filter(id=url_id).first()

        if url_tracker_obj is None:
            return CustomResponse(
                general_message="No URL related data available"
            ).get_failure_response()
            
        queryset = UrlShortenerTracker.objects.filter(url_shortener_id = url_tracker_obj.id)
        device_counts = UrlShortenerTracker.objects.values('device_type').annotate(count=Count('device_type')).order_by('device_type')
        platform_counts = UrlShortenerTracker.objects.values('operating_system').annotate(count=Count('operating_system')).order_by('operating_system')
        browser_counts = UrlShortenerTracker.objects.values('browser').annotate(count=Count('browser')).order_by('browser')
        
        countset={}
        countset[1] = device_counts
        countset[2] = platform_counts
        countset[3] = browser_counts
        
        print(countset)
        paginated_queryset = CommonUtils.get_paginated_queryset(
            queryset,
            request,
            ["id","ip_address","device_type","operating_system","browser",]

        )

        serializer = ShowShortenUrlsTrackerSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )

        return CustomResponse(
            general_message="URL Stats",
            response=countset
                ).paginated_response(
                    data=serializer.data,
                    pagination=paginated_queryset.get(
                        "pagination"
                    )
                )


            
