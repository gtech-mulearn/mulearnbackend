import uuid

from rest_framework.views import APIView

from db.campus import CampusExecom
from db.organization import Organization
from db.user import Role, User
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType

from api.dashboard.campus.dash_campus_helper import validate_campus_member
from . import serializers as campus_serializers


class CampusExecomAPI(APIView):
    authentication_classes = [CustomizePermission]

    @staticmethod
    def _get_campus(campus_id):
        return Organization.objects.filter(
            id=campus_id,
            org_type=OrganizationType.COLLEGE.value,
        ).first()

    @role_required([RoleType.ADMIN.value])
    def get(self, request, campus_id):
        if not (campus := self._get_campus(campus_id)):
            return CustomResponse(general_message="Campus not found").get_failure_response()

        members = (
            CampusExecom.objects.filter(campus=campus)
            .select_related("user", "role")
            .order_by("role__title", "user__full_name")
        )
        serializer = campus_serializers.CampusExecomMemberSerializer(members, many=True)
        return CustomResponse(response={"data": serializer.data}).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def post(self, request, campus_id):
        acting_user_id = JWTUtils.fetch_user_id(request)

        if not (campus := self._get_campus(campus_id)):
            return CustomResponse(general_message="Campus not found").get_failure_response()

        serializer = campus_serializers.CampusExecomAssignSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        uid = serializer.validated_data["uid"]
        role_title = serializer.validated_data["role_title"]

        if not (member := User.objects.filter(id=uid).first()):
            return CustomResponse(general_message="User not found").get_failure_response()

        if not validate_campus_member(uid, campus.id):
            return CustomResponse(
                general_message="User is not an active member of this campus"
            ).get_failure_response()

        role = Role.objects.filter(title=role_title).first()
        if role is None:
            role = Role.objects.create(
                id=str(uuid.uuid4()),
                title=role_title,
                created_by_id=acting_user_id,
                updated_by_id=acting_user_id,
            )

        existing_member = CampusExecom.objects.filter(campus=campus, role=role).first()
        if existing_member:
            existing_member.user = member
            existing_member.updated_by_id = acting_user_id
            existing_member.save(update_fields=["user", "updated_by", "updated_at"])
            message = "Role reassigned successfully"
            execom_member = existing_member
        else:
            execom_member = CampusExecom.objects.create(
                id=str(uuid.uuid4()),
                campus=campus,
                user=member,
                role=role,
                created_by_id=acting_user_id,
                updated_by_id=acting_user_id,
            )
            message = "Member added to campus execom"

        member_response = campus_serializers.CampusExecomMemberSerializer(execom_member).data
        return CustomResponse(
            general_message=message,
            response={"data": member_response},
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, campus_id, uid):
        if not self._get_campus(campus_id):
            return CustomResponse(general_message="Campus not found").get_failure_response()

        deleted_count, _ = CampusExecom.objects.filter(
            campus_id=campus_id,
            user_id=uid,
        ).delete()

        if deleted_count == 0:
            return CustomResponse(
                general_message="User is not part of the campus execom"
            ).get_failure_response()

        return CustomResponse(
            general_message="Member removed from campus execom"
        ).get_success_response()
