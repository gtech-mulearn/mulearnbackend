import csv
import io
from datetime import datetime

from django.utils import timezone
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from db.career_lab import Hiring
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from . import career_lab_serializers

CAREER_LAB_ADMIN_ROLES = [RoleType.ADMIN.value, RoleType.ASSOCIATE.value]

SEARCH_FIELDS = ["role", "organization", "title", "location"]
SORT_FIELDS = {
    "lastdate": "lastdate",
    "posted_date": "posted_date",
    "organization": "organization",
    "role": "role",
    "created_at": "created_at",
}


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _apply_filters(queryset, request):
    """Shared filter set for admin and public hiring list endpoints."""
    params = request.query_params

    status = params.get("status")
    today = timezone.now().date()
    if status == "ongoing":
        queryset = queryset.filter(lastdate__gte=today)
    elif status == "previous":
        queryset = queryset.filter(lastdate__lt=today)

    if organization := params.get("organization"):
        queryset = queryset.filter(organization__icontains=organization)

    if role := params.get("role"):
        queryset = queryset.filter(role__icontains=role)

    if location := params.get("location"):
        queryset = queryset.filter(location__icontains=location)

    if duration := params.get("duration"):
        queryset = queryset.filter(duration__icontains=duration)

    if title := params.get("title"):
        queryset = queryset.filter(title__icontains=title)

    if min_vacancies := params.get("min_vacancies"):
        try:
            queryset = queryset.filter(vacancies__gte=int(min_vacancies))
        except ValueError:
            pass

    if max_vacancies := params.get("max_vacancies"):
        try:
            queryset = queryset.filter(vacancies__lte=int(max_vacancies))
        except ValueError:
            pass

    if lastdate_from := params.get("lastdate_from"):
        if parsed := _parse_date(lastdate_from):
            queryset = queryset.filter(lastdate__gte=parsed)

    if lastdate_to := params.get("lastdate_to"):
        if parsed := _parse_date(lastdate_to):
            queryset = queryset.filter(lastdate__lte=parsed)

    if posted_from := params.get("posted_date_from"):
        if parsed := _parse_date(posted_from):
            queryset = queryset.filter(posted_date__gte=parsed)

    if posted_to := params.get("posted_date_to"):
        if parsed := _parse_date(posted_to):
            queryset = queryset.filter(posted_date__lte=parsed)

    return queryset


FILTER_PARAMETERS = [
    OpenApiParameter("status", OpenApiTypes.STR, description="ongoing | previous | all"),
    OpenApiParameter("organization", OpenApiTypes.STR),
    OpenApiParameter("role", OpenApiTypes.STR),
    OpenApiParameter("location", OpenApiTypes.STR),
    OpenApiParameter("title", OpenApiTypes.STR),
    OpenApiParameter("duration", OpenApiTypes.STR),
    OpenApiParameter("min_vacancies", OpenApiTypes.INT),
    OpenApiParameter("max_vacancies", OpenApiTypes.INT),
    OpenApiParameter("lastdate_from", OpenApiTypes.DATE),
    OpenApiParameter("lastdate_to", OpenApiTypes.DATE),
    OpenApiParameter("posted_date_from", OpenApiTypes.DATE),
    OpenApiParameter("posted_date_to", OpenApiTypes.DATE),
    OpenApiParameter("search", OpenApiTypes.STR, description="Search role/organization/title/location"),
    OpenApiParameter("sortBy", OpenApiTypes.STR),
    OpenApiParameter("pageIndex", OpenApiTypes.INT),
    OpenApiParameter("perPage", OpenApiTypes.INT),
]


class HiringAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Career Lab'],
        description="List hiring postings with filters.",
        parameters=FILTER_PARAMETERS,
        responses={200: career_lab_serializers.HiringSerializer(many=True)},
    )
    @role_required(CAREER_LAB_ADMIN_ROLES)
    def get(self, request):
        queryset = _apply_filters(Hiring.objects.all().order_by("-posted_date"), request)
        paginated_queryset = CommonUtils.get_paginated_queryset(
            queryset, request,
            search_fields=SEARCH_FIELDS,
            sort_fields=SORT_FIELDS,
        )
        serializer = career_lab_serializers.HiringSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Career Lab'],
        description="Create a new hiring posting.",
        request=career_lab_serializers.HiringSerializer,
        responses={200: career_lab_serializers.HiringSerializer},
    )
    @role_required(CAREER_LAB_ADMIN_ROLES)
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = career_lab_serializers.HiringSerializer(data=request.data, context={"user_id": user_id})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Hiring posting created successfully.",
                response=serializer.data,
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class HiringDetailAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Career Lab'],
        description="Retrieve a specific hiring posting.",
        responses={200: career_lab_serializers.HiringSerializer},
    )
    @role_required(CAREER_LAB_ADMIN_ROLES)
    def get(self, request, hiring_id):
        hiring = Hiring.objects.filter(id=hiring_id).first()
        if not hiring:
            return CustomResponse(general_message="Hiring posting not found.").get_failure_response(status_code=404)
        serializer = career_lab_serializers.HiringSerializer(hiring)
        return CustomResponse(response=serializer.data).get_success_response()

    @extend_schema(
        tags=['Dashboard - Career Lab'],
        description="Update a specific hiring posting.",
        request=career_lab_serializers.HiringSerializer,
        responses={200: career_lab_serializers.HiringSerializer},
    )
    @role_required(CAREER_LAB_ADMIN_ROLES)
    def put(self, request, hiring_id):
        user_id = JWTUtils.fetch_user_id(request)
        hiring = Hiring.objects.filter(id=hiring_id).first()
        if not hiring:
            return CustomResponse(general_message="Hiring posting not found.").get_failure_response(status_code=404)
        serializer = career_lab_serializers.HiringSerializer(
            hiring, data=request.data, partial=True, context={"user_id": user_id}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Hiring posting updated successfully.",
                response=serializer.data,
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    @extend_schema(
        tags=['Dashboard - Career Lab'],
        description="Delete a specific hiring posting.",
    )
    @role_required(CAREER_LAB_ADMIN_ROLES)
    def delete(self, request, hiring_id):
        hiring = Hiring.objects.filter(id=hiring_id).first()
        if not hiring:
            return CustomResponse(general_message="Hiring posting not found.").get_failure_response(status_code=404)
        hiring.delete()
        return CustomResponse(general_message="Hiring posting deleted successfully.").get_success_response()


class HiringCSVAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Career Lab'],
        description="Export hiring postings as CSV.",
        parameters=FILTER_PARAMETERS,
    )
    @role_required(CAREER_LAB_ADMIN_ROLES)
    def get(self, request):
        queryset = _apply_filters(Hiring.objects.all(), request)
        serializer = career_lab_serializers.HiringSerializer(queryset, many=True)
        return CommonUtils.generate_csv(serializer.data, "Hiring")

    @extend_schema(
        tags=['Dashboard - Career Lab'],
        description=(
            "Bulk import hiring postings from a CSV file. "
            "Expected columns: posted_date, role, organization, title, location, lastdate, "
            "applylink, jdlink, duration, remuneration, vacancies, extracontent. "
            "Import is create-only — existing rows are never updated."
        ),
    )
    @role_required(CAREER_LAB_ADMIN_ROLES)
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        csv_file = request.FILES.get('file')
        if not csv_file:
            return CustomResponse(general_message="No CSV file provided.").get_failure_response()

        try:
            decoded_file = csv_file.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            return CustomResponse(general_message="Unable to decode CSV file. Please upload a UTF-8 encoded CSV.").get_failure_response()

        reader = csv.DictReader(io.StringIO(decoded_file))

        created_count = 0
        row_errors = []
        for row_number, row in enumerate(reader, start=2):
            cleaned_row = {key: (value if value not in ("", None) else None) for key, value in row.items()}
            serializer = career_lab_serializers.HiringCSVRowSerializer(
                data=cleaned_row, context={"user_id": user_id}
            )
            if serializer.is_valid():
                serializer.save()
                created_count += 1
            else:
                row_errors.append({"row": row_number, "errors": serializer.errors})

        return CustomResponse(
            general_message=f"Imported {created_count} hiring posting(s).",
            response={"created": created_count, "errors": row_errors},
        ).get_success_response()


class PublicOngoingHiringAPI(APIView):
    permission_classes = []

    @extend_schema(
        tags=['Public - Career Lab'],
        description="Public endpoint to list ongoing hiring postings.",
        parameters=FILTER_PARAMETERS,
        responses={200: career_lab_serializers.PublicOngoingHiringSerializer(many=True)},
    )
    def get(self, request):
        queryset = Hiring.objects.filter(lastdate__gte=timezone.now().date()).order_by("-posted_date")
        queryset = _apply_filters(queryset, request)
        paginated_queryset = CommonUtils.get_paginated_queryset(
            queryset, request,
            search_fields=SEARCH_FIELDS,
            sort_fields=SORT_FIELDS,
        )
        serializer = career_lab_serializers.PublicOngoingHiringSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class PublicPreviousHiringAPI(APIView):
    permission_classes = []

    @extend_schema(
        tags=['Public - Career Lab'],
        description="Public endpoint to list previous/archived hiring postings.",
        parameters=FILTER_PARAMETERS,
        responses={200: career_lab_serializers.PublicPreviousHiringSerializer(many=True)},
    )
    def get(self, request):
        queryset = Hiring.objects.filter(lastdate__lt=timezone.now().date()).order_by("-posted_date")
        queryset = _apply_filters(queryset, request)
        paginated_queryset = CommonUtils.get_paginated_queryset(
            queryset, request,
            search_fields=SEARCH_FIELDS,
            sort_fields=SORT_FIELDS,
        )
        serializer = career_lab_serializers.PublicPreviousHiringSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()
