from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.storage import FileSystemStorage
from django.core.validators import URLValidator
from django.db import transaction
from rest_framework.views import APIView

from db.impact_project import ImpactProject, ImpactProjectLink, ImpactProjectUserLink
from db.task import InterestGroup
from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse

from .dash_ig_view import _can_manage_ig
from .impact_project_serializer import (
    ImpactProjectCreateUpdateSerializer,
    ImpactProjectSerializer,
)

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _resolve_team(team_data):
    """Resolve muids to users, deduping repeats. Raises ValueError on any unknown muid
    so the caller can 400 instead of silently saving a team missing its lead."""
    seen_muids = set()
    resolved = []
    for member in team_data:
        muid = member.get("muid")
        if not muid or muid in seen_muids:
            continue
        seen_muids.add(muid)
        user = User.objects.filter(muid=muid).first()
        if not user:
            raise ValueError(f"No user found with muid '{muid}'")
        resolved.append((user, bool(member.get("is_lead"))))
    return resolved


def _validate_links(links_data):
    validator = URLValidator()
    for link in links_data:
        label, url = link.get("label"), link.get("url")
        if not label or not url:
            raise ValueError("Each link requires both a 'label' and a 'url'.")
        if len(label) > 50:
            raise ValueError(f"Link label '{label}' exceeds 50 characters.")
        if len(url) > 500:
            raise ValueError(f"Link url for '{label}' exceeds 500 characters.")
        try:
            validator(url)
        except DjangoValidationError:
            raise ValueError(f"'{url}' is not a valid URL.")


def _sync_links(project, links_data):
    _validate_links(links_data)
    ImpactProjectLink.objects.filter(project=project).delete()
    for link in links_data:
        ImpactProjectLink.objects.create(project=project, label=link["label"], url=link["url"])


class ImpactProjectListCreateAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request, ig_id):
        ig = InterestGroup.objects.filter(id=ig_id).first()
        if not ig:
            return CustomResponse(general_message="Interest Group Does Not Exist").get_failure_response()

        projects = ImpactProject.objects.filter(ig=ig).select_related("created_by", "updated_by")
        serializer = ImpactProjectSerializer(projects, many=True)
        return CustomResponse(response={"impactProjects": serializer.data}).get_success_response()

    @transaction.atomic
    def post(self, request, ig_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        ig = InterestGroup.objects.filter(id=ig_id).first()
        if not ig:
            return CustomResponse(general_message="Interest Group Does Not Exist").get_failure_response()

        if not _can_manage_ig(roles, ig):
            return CustomResponse(
                general_message="You do not have permission to manage this Interest Group"
            ).get_failure_response()

        request_data = request.data.copy()
        request_data["ig"] = ig.id
        request_data["created_by"] = request_data["updated_by"] = user_id

        serializer = ImpactProjectCreateUpdateSerializer(data=request_data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        try:
            resolved_team = _resolve_team(request_data.get("team", []))
            _validate_links(request_data.get("links", []))
        except ValueError as exc:
            return CustomResponse(general_message=str(exc)).get_failure_response()

        project = serializer.save()
        ImpactProjectUserLink.objects.filter(project=project).delete()
        for user, is_lead in resolved_team:
            ImpactProjectUserLink.objects.create(project=project, user=user, is_lead=is_lead)
        _sync_links(project, request_data.get("links", []))

        return CustomResponse(
            response={"impactProject": ImpactProjectSerializer(project).data}
        ).get_success_response()


class ImpactProjectDetailAPI(APIView):
    authentication_classes = [CustomizePermission]

    def _get_project(self, ig_id, project_id):
        return ImpactProject.objects.filter(id=project_id, ig_id=ig_id).first()

    @transaction.atomic
    def patch(self, request, ig_id, project_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        ig = InterestGroup.objects.filter(id=ig_id).first()
        if not ig:
            return CustomResponse(general_message="Interest Group Does Not Exist").get_failure_response()

        if not _can_manage_ig(roles, ig):
            return CustomResponse(
                general_message="You do not have permission to manage this Interest Group"
            ).get_failure_response()

        project = self._get_project(ig_id, project_id)
        if not project:
            return CustomResponse(general_message="Impact Project Does Not Exist").get_failure_response()

        request_data = request.data.copy()
        request_data["updated_by"] = user_id
        # ig and created_by are immutable via this endpoint — an IG lead must not be able
        # to reassign a project to another IG or forge its original creator.
        request_data.pop("ig", None)
        request_data.pop("created_by", None)

        serializer = ImpactProjectCreateUpdateSerializer(
            data=request_data, instance=project, partial=True
        )
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        try:
            if "team" in request_data:
                resolved_team = _resolve_team(request_data.get("team", []))
            if "links" in request_data:
                _validate_links(request_data.get("links", []))
        except ValueError as exc:
            return CustomResponse(general_message=str(exc)).get_failure_response()

        project = serializer.save()
        if "team" in request_data:
            ImpactProjectUserLink.objects.filter(project=project).delete()
            for user, is_lead in resolved_team:
                ImpactProjectUserLink.objects.create(project=project, user=user, is_lead=is_lead)
        if "links" in request_data:
            _sync_links(project, request_data.get("links", []))

        return CustomResponse(
            response={"impactProject": ImpactProjectSerializer(project).data}
        ).get_success_response()

    def delete(self, request, ig_id, project_id):
        roles = JWTUtils.fetch_role(request)

        ig = InterestGroup.objects.filter(id=ig_id).first()
        if not ig:
            return CustomResponse(general_message="Interest Group Does Not Exist").get_failure_response()

        if not _can_manage_ig(roles, ig):
            return CustomResponse(
                general_message="You do not have permission to manage this Interest Group"
            ).get_failure_response()

        project = self._get_project(ig_id, project_id)
        if not project:
            return CustomResponse(general_message="Impact Project Does Not Exist").get_failure_response()

        fs = FileSystemStorage()
        image_path = f"impact_project/image/{project.id}.png"
        if fs.exists(image_path):
            fs.delete(image_path)

        project.delete()
        return CustomResponse(general_message="Impact Project deleted successfully").get_success_response()


class ImpactProjectImageAPI(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request, ig_id, project_id):
        roles = JWTUtils.fetch_role(request)

        ig = InterestGroup.objects.filter(id=ig_id).first()
        if not ig:
            return CustomResponse(general_message="Interest Group Does Not Exist").get_failure_response()

        if not _can_manage_ig(roles, ig):
            return CustomResponse(
                general_message="You do not have permission to manage this Interest Group"
            ).get_failure_response()

        project = ImpactProject.objects.filter(id=project_id, ig_id=ig_id).first()
        if not project:
            return CustomResponse(general_message="Impact Project Does Not Exist").get_failure_response()

        image = request.FILES.get("image")
        if image is None:
            return CustomResponse(general_message="No image provided").get_failure_response()

        if not image.content_type.startswith("image/"):
            return CustomResponse(general_message="Expected an image file").get_failure_response()

        if image.size > MAX_IMAGE_SIZE_BYTES:
            return CustomResponse(general_message="Image must be under 5 MB").get_failure_response()

        fs = FileSystemStorage()
        filename = f"impact_project/image/{project.id}.png"
        if fs.exists(filename):
            fs.delete(filename)
        fs.save(filename, image)

        return CustomResponse(response={"image": project.image}).get_success_response()
