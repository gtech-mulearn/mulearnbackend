from django.db import transaction
from rest_framework.views import APIView

from db.organization import College, Organization, UserOrganizationLink
from db.user import User
from utils.permission import JWTUtils
from utils.response import CustomResponse
from utils.types import OrganizationType
from utils.utils import CommonUtils
from .serializer import (
    CollegeListSerializer,
    CollegeChangeSerializer,
)

class CollegeApi(APIView):
    def get(self, request, college_code=None):
        if college_code:
            colleges = College.objects.filter(id=college_code)
        else:
            colleges = College.objects.all().select_related("org")

        paginated_queryset = CommonUtils.get_paginated_queryset(
            colleges,
            request,
            search_fields=["org__title", ],
            sort_fields={'org': 'org'},
        )
        serializer = CollegeListSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )

class CollegeChangeAPI(APIView):
    def patch(self, request):
        
        user_id = JWTUtils.fetch_user_id(request)
        serializer = CollegeChangeSerializer(data=request.data)

        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors
            ).get_failure_response()

        college_code = serializer.validated_data["college_code"]

        try:
            new_organization = Organization.objects.get(
                code=college_code,
                org_type=OrganizationType.COLLEGE.value
            )

            with transaction.atomic():
                user = User.objects.get(id=user_id)       
                existing_college_links = UserOrganizationLink.objects.filter(
                    user_id=user_id,
                    org__org_type=OrganizationType.COLLEGE.value
                )
                
                if existing_college_links.exists():
                    user_org_link = existing_college_links.first()
                    user_org_link.org = new_organization
                    user_org_link.verified = False
                    user_org_link.save()
                    created = False
                else:
                    user_org_link = UserOrganizationLink.objects.create(
                        user=user,
                        org=new_organization,
                        verified=False,
                        created_by=user,
                    )
                    created = True

                message = (
                    f"Successfully linked to {new_organization.title}"
                    if created else
                    f"Successfully changed college to {new_organization.title}"
                )

            return CustomResponse(
                general_message=message
            ).get_success_response()

        except Organization.DoesNotExist:
            return CustomResponse(
                general_message="College with provided code not found"
            ).get_failure_response()

        except Exception as e:
            return CustomResponse(
                general_message=f"Error updating college: {str(e)}"
            ).get_failure_response()
