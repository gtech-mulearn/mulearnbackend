from django.db import transaction
from rest_framework.views import APIView

from db.organization import College, Organization, UserOrganizationLink, Department
from db.user import User
from utils.permission import JWTUtils
from utils.response import CustomResponse
from utils.types import OrganizationType
from utils.utils import CommonUtils
from drf_spectacular.utils import extend_schema
from .serializer import (
    CollegeListSerializer,
    CollegeChangeSerializer,
)

class CollegeApi(APIView):
    @extend_schema(
        tags=['Dashboard - College'],
        description="Retrieve College Api.",
        responses={200: CollegeListSerializer},
    )
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
    @extend_schema(
        tags=['Dashboard - College'],
        description="Partially update College Change.",
        request=CollegeChangeSerializer,
        responses={200: CollegeChangeSerializer},
    )
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
                ).order_by('-created_at', '-id')

                if existing_links.exists():
                    current_link = existing_links.select_related('department').first()

                    # Dedupe: a user should only ever have one college link. Drop any
                    # extras so the final .get() below can't raise MultipleObjectsReturned.
                    duplicate_ids = list(
                        existing_links.exclude(id=current_link.id).values_list('id', flat=True)
                    )
                    if duplicate_ids:
                        UserOrganizationLink.objects.filter(id__in=duplicate_ids).delete()

                    current_link.org = new_organization
                    # Auto-verified: there is no manual campus-transfer approval
                    # flow, so leaving this False would strand the student
                    # unverified at both the old and new campus indefinitely.
                    current_link.verified = True
                    if department_id is not None:
                        current_link.department = department
                    current_link.save()
                    final_department = current_link.department

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
                        if final_department:
                            message = (
                                f"College updated successfully to {new_organization.title}. "
                                f"Department remains {final_department.title}"
                            )
                        else:
                            message = f"College updated successfully to {new_organization.title}"

                    action = "updated"
                else:
                    new_link = UserOrganizationLink.objects.create(
                        user=user,
                        org=new_organization,
                        department=department,
                        verified=True,
                        created_by=user,
                    )
                    final_department = new_link.department

                    if department:
                        message = (
                            f"College linked successfully to {new_organization.title}. "
                            f"Department set to {department.title}"
                        )
                    else:
                        message = f"College linked successfully to {new_organization.title}"

                    action = "created"

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
