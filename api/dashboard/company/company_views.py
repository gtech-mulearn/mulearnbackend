from rest_framework.views import APIView
from django.db.models import Q
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.company import Company
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from . import serializers

class CompanyRegistrationAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Submit a new company registration.",
        request=serializers.CompanyRegisterSerializer,
        responses={200: serializers.CompanyRegisterSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        if Company.objects.filter(company_user_id=user_id).exists():
            return CustomResponse(
                general_message="A company request already exists for your account."
            ).get_failure_response()

        serializer = serializers.CompanyRegisterSerializer(
            data=request.data, context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Company registration submitted successfully.",
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Update or resubmit a pending/rejected company registration.",
        request=serializers.CompanyUpdateSerializer,
        responses={200: serializers.CompanyUpdateSerializer},
    )
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id).first()

        if not company:
            return CustomResponse(
                general_message="No company registration request found for your account."
            ).get_failure_response(status_code=404)

        if company.status == "verified":
            return CustomResponse(
                general_message="Your company is already verified. Please use the profile endpoint to update your details."
            ).get_failure_response()

        serializer = serializers.CompanyUpdateSerializer(
            company, data=request.data, partial=True, context={"user_id": user_id}
        )

        if serializer.is_valid():
        
            if company.status == "rejected":
                serializer.save(status="pending", rejection_reason=None)
                msg = "Company registration updated and resubmitted successfully."
            else:
                serializer.save()
                msg = "Company registration updated successfully."

            return CustomResponse(
                general_message=msg,
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class CompanyStatusAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Check the status of a company registration.",
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        company = Company.objects.filter(company_user_id=user_id).first()
        if not company:
            return CustomResponse(
                general_message="No company request found for your account."
            ).get_failure_response(status_code=404)
            
        return CustomResponse(
            response={
                "status": company.status,
                "rejection_reason": company.rejection_reason,
                "company_id": company.id,
                "name": company.name,
                "slug": company.slug
            }
        ).get_success_response()

class CompanyProfileAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Retrieve the profile of a verified company.",
        responses={200: serializers.CompanyDetailSerializer},
    )
    @role_required([RoleType.COMPANY.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id).first()
        
        if not company:
            return CustomResponse(
                general_message="Company profile not found."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.CompanyDetailSerializer(company)
        return CustomResponse(response=serializer.data).get_success_response()

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Update the profile of a verified company.",
        request=serializers.CompanyUpdateSerializer,
        responses={200: serializers.CompanyUpdateSerializer},
    )
    @role_required([RoleType.COMPANY.value])
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id).first()
        
        if not company:
            return CustomResponse(
                general_message="Company profile not found."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.CompanyUpdateSerializer(
            company, data=request.data, partial=True, context={"user_id": user_id}
        )
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Company profile updated successfully.",
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class CompanyListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="List all companies with filtering.",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("industry_sector", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("company_size", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("district", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("state", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("country", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: serializers.CompanyListSerializer(many=True)},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        companies = Company.objects.all()

        status = request.query_params.get("status")
        industry_sector = request.query_params.get("industry_sector")
        company_size = request.query_params.get("company_size")
        district = request.query_params.get("district")
        state = request.query_params.get("state")
        country = request.query_params.get("country")

        if status:
            companies = companies.filter(status=status)
        if industry_sector:
            companies = companies.filter(industry_sector=industry_sector)
        if company_size:
            companies = companies.filter(company_size=company_size)
        if district:
            companies = companies.filter(district__name=district)
        if state:
            companies = companies.filter(district__zone__state__name=state)
        if country:
            companies = companies.filter(district__zone__state__country__name=country)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            companies, request, 
            search_fields=["name", "slug", "email", "industry_sector"],
            sort_fields={"name": "name", "status": "status", "created_at": "created_at"}
        )
        
        serializer = serializers.CompanyListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

class CompanyDetailAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Get details of a specific company by ID.",
        responses={200: serializers.CompanyDetailSerializer},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request, company_id):
        company = Company.objects.filter(id=company_id).first()
        if not company:
            return CustomResponse(
                general_message="Company not found."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.CompanyDetailSerializer(company)
        return CustomResponse(response=serializer.data).get_success_response()

class CompanyVerifyAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Verify or reject a company.",
        request=serializers.CompanyVerifySerializer,
    )
    @role_required([RoleType.ADMIN.value])
    def patch(self, request, company_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(id=company_id).first()
        
        if not company:
            return CustomResponse(
                general_message="Company not found."
            ).get_failure_response(status_code=404)
            
        if company.status == "verified":
            return CustomResponse(
                general_message="Company is already verified."
            ).get_failure_response()
            
        serializer = serializers.CompanyVerifySerializer(
            company, data=request.data, context={"user_id": user_id}
        )
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message=f"Company status updated to {serializer.validated_data.get('status')} successfully."
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class PublicCompanyProfileAPI(APIView):
    permission_classes = []

    @extend_schema(
        tags=['Public - Company'],
        description="Public endpoint to view a company's profile.",
        responses={200: serializers.PublicCompanyProfileSerializer},
    )
    def get(self, request, slug):
        company = Company.objects.filter(slug=slug, status="verified").first()
        if not company:
            return CustomResponse(
                general_message="Company not found."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.PublicCompanyProfileSerializer(company)
        return CustomResponse(response=serializer.data).get_success_response()
