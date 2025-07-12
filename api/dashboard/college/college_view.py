from django.db import transaction
from rest_framework.views import APIView

from db.organization import College, Organization, UserOrganizationLink, Department
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
            search_fields=["org__title"],
            sort_fields={'org': 'org'},
        )
        serializer = CollegeListSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, 
            pagination=paginated_queryset.get("pagination")
        )


class CollegeChangeAPI(APIView):
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = CollegeChangeSerializer(data=request.data)

        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        org_id = serializer.validated_data["org_id"]
        department_id = serializer.validated_data.get("department_id")

        try:
            user = User.objects.get(id=user_id)
            new_organization = Organization.objects.get(
                id=org_id,
                org_type=OrganizationType.COLLEGE.value
            )
            department = Department.objects.get(id=department_id) if department_id else None

            with transaction.atomic():
                existing_links = UserOrganizationLink.objects.filter(
                    user_id=user_id,
                    org__org_type=OrganizationType.COLLEGE.value
                )

                if existing_links.exists():
                    update_data = {
                        'org': new_organization,
                        'verified': False
                    }
                    
                    if department_id is not None:
                        update_data['department'] = department
                    
                    existing_links.update(**update_data)
                    current_link = existing_links.select_related('department').first()
                    current_department = current_link.department
                    
                    if department_id is not None:
                        if department:
                            message = (
                                f"College updated successfully to {new_organization.title}. "
                                f"Department updated to {department.title}"
                            )
                        else:
                            message = (
                                f"College updated successfully to {new_organization.title}. "
                                f"Department removed"
                            )
                    else:
                        if current_department:
                            message = (
                                f"College updated successfully to {new_organization.title}. "
                                f"Department remains {current_department.title}"
                            )
                        else:
                            message = f"College updated successfully to {new_organization.title}"
                    
                    action = "updated"
                else:
                    UserOrganizationLink.objects.create(
                        user=user,
                        org=new_organization,
                        department=department,
                        verified=False,
                        created_by=user,
                    )
                    
                    if department:
                        message = (
                            f"College linked successfully to {new_organization.title}. "
                            f"Department set to {department.title}"
                        )
                    else:
                        message = f"College linked successfully to {new_organization.title}"
                    
                    action = "created"

            final_link = UserOrganizationLink.objects.select_related('department').get(
                user_id=user_id,
                org__org_type=OrganizationType.COLLEGE.value
            )
            final_department = final_link.department

            return CustomResponse(
                general_message=message, 
                response={
                    "org_id": new_organization.id,
                    "org_title": new_organization.title,
                    "department_id": final_department.id if final_department else None,
                    "department_title": final_department.title if final_department else None,
                    "action": action
                }
            ).get_success_response()

        except User.DoesNotExist:
            return CustomResponse(
                general_message="User not found"
            ).get_failure_response()
        except Organization.DoesNotExist:
            return CustomResponse(
                general_message="College with provided ID not found"
            ).get_failure_response()
        except Department.DoesNotExist:
            return CustomResponse(
                general_message="Department with provided ID not found"
            ).get_failure_response()
        except Exception as e:
            return CustomResponse(
                general_message=f"Error processing college request: {str(e)}"
            ).get_failure_response()
