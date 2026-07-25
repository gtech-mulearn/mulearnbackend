from django.db.models import Q
from rest_framework.views import APIView
from utils.utils import CommonUtils, ImageUploadUtils
from utils.response import CustomResponse
from utils.permission import CustomizePermission, JWTUtils
from db.projects import (
    Project,
    ProjectImage,
    ProjectLink,
    ProjectSkillLink,
    Comment,
    Vote,
    ProjectMember,
)
from db.user import User
from drf_spectacular.utils import extend_schema
from .projects_serializer import (
    ProjectSerializer,
    ProjectUpdateSerializer,
    CommentSerializer,
    VoteSerializer,
    AddMemberSerializer,
    ProjectMemberSerializer,
)


class ProjectDetailAPIView(APIView):
    authentication_classes = [CustomizePermission]
    @extend_schema(
        tags=['Dashboard - Projects'],
        description="Retrieve Project Detail.",
        responses={200: ProjectSerializer},
    )
    def get(self, request, pk=None):
        if pk is not None:
            project = Project.objects.get(id=pk)
            serializer = ProjectSerializer(project)
            return CustomResponse(
                response={"Project": serializer.data}
            ).get_success_response()
        else:
            return CustomResponse(
                general_message="no Project id provided"
            ).get_failure_response()
            
    @extend_schema(
        tags=['Dashboard - Projects'],
        description="Update Project Detail.",
        responses={200: ProjectSerializer},
    )
    def put(self, request, pk=None):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))
        if pk is None:
            return CustomResponse(
                general_message="no Project id provided"
            ).get_failure_response()
        project = Project.objects.get(id=pk)
        images_data = request.FILES.getlist('images')
        if images_data:
            error = _validate_project_images(images_data)
            if error:
                return CustomResponse(general_message=error).get_failure_response()
        serializer = ProjectUpdateSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by = user)
            if images_data:
                ProjectImage.objects.filter(project=project).delete()
                for image_data in images_data:
                    ProjectImage.objects.create(project=project, image=image_data)
            links = serializer.validated_data.get("links_json")
            skill_ids = serializer.validated_data.get("skill_ids_json")
            if links is not None:
                _replace_links(project, links)
            if skill_ids is not None:
                _replace_skills(project, skill_ids)
            read_serializer = ProjectSerializer(serializer.instance)
            return CustomResponse(
                response={"Project": read_serializer.data}
            ).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @extend_schema(tags=['Dashboard - Projects'], description="Delete Project Detail.",
        responses={200: ProjectSerializer},
    )
    def delete(self, request, pk=None):
        if pk is not None:
            try:
                project = Project.objects.get(id=pk)
                project.delete()
                return CustomResponse(
                    general_message="Project deleted successfully"
                ).get_success_response()
            except Project.DoesNotExist:
                return CustomResponse(
                    general_message="Project not found"
                ).get_failure_response()
        else:
            return CustomResponse(
                general_message="no Project id provided"
            ).get_failure_response()


def _validate_project_images(images_data):
    """Returns an error message string if any image is invalid, else None."""
    for image_data in images_data:
        error = ImageUploadUtils.validate(image_data)
        if error:
            return error
    return None


def _replace_links(project, links):
    ProjectLink.objects.filter(project=project).delete()
    for i, item in enumerate(links):
        ProjectLink.objects.create(
            project=project,
            label=item["label"].strip(),
            url=item["url"].strip(),
            position=item.get("position", i),
        )


def _replace_skills(project, skill_ids):
    ProjectSkillLink.objects.filter(project=project).delete()
    for sid in skill_ids:
        ProjectSkillLink.objects.create(project=project, skill_id=sid)


class ProjectStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Projects'],
        description="Partially update Project Status.",
        responses={200: ProjectSerializer},
    )
    def patch(self, request, pk):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))
        try:
            project = Project.objects.get(id=pk)
        except Project.DoesNotExist:
            return CustomResponse(general_message="project not found").get_failure_response()
        if project.created_by_id != user.id:
            return CustomResponse(general_message="only owner can change status").get_failure_response()
        new_status = request.data.get("status")
        if new_status not in dict(Project.STATUS_CHOICES):
            return CustomResponse(general_message="invalid status").get_failure_response()
        project.status = new_status
        project.updated_by = user
        project.save()
        return CustomResponse(response={"Project": ProjectSerializer(project).data}).get_success_response()


class ProjectsAPIView(APIView):
    authentication_classes = [CustomizePermission]
    @extend_schema(
        tags=['Dashboard - Projects'],
        description="Retrieve Projects.",
        responses={200: ProjectSerializer},
    )
    def get(self, request):
        viewer_id = JWTUtils.fetch_user_id(request)

        qs = (Project.objects.all()
              .select_related("created_by", "updated_by")
              .prefetch_related("images", "links", "skill_links__skill",
                                "members__user", "votes", "comments"))

        muid = request.query_params.get("muid")
        created_by = request.query_params.get("created_by")
        status = request.query_params.get("status")

        owner_id_for_visibility = None
        if muid:
            qs = qs.filter(Q(created_by__muid=muid) | Q(members__user__muid=muid)).distinct()
            owner_user = User.objects.filter(muid=muid).only("id").first()
            owner_id_for_visibility = owner_user.id if owner_user else None
        elif created_by:
            qs = qs.filter(created_by_id=created_by)
            owner_id_for_visibility = created_by

        if status:
            qs = qs.filter(status=status)
        else:
            if owner_id_for_visibility and owner_id_for_visibility != viewer_id:
                qs = qs.filter(status="published")
            elif not owner_id_for_visibility:
                qs = qs.filter(status="published")

        paginated = CommonUtils.get_paginated_queryset(
            queryset=qs, request=request,
            search_fields=["title", "description"],
            sort_fields={"created_at": "created_at"},
            is_pagination=True,
        )
        return CustomResponse().paginated_response(
            data={"Projects": ProjectSerializer(paginated["queryset"], many=True).data},
            pagination=paginated["pagination"],
        )
        
    @extend_schema(
        tags=['Dashboard - Projects'],
        description="Create Projects.",
        request=ProjectUpdateSerializer,
        responses={200: ProjectSerializer},
    )
    def post(self, request):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))
        images_data = request.FILES.getlist('images')
        if images_data:
            error = _validate_project_images(images_data)
            if error:
                return CustomResponse(general_message=error).get_failure_response()
        data = request.data.copy()
        if 'images' in data:
            del data['images']
        serializer = ProjectUpdateSerializer(data=data)
        if serializer.is_valid():
            links = serializer.validated_data.get("links_json", [])
            skill_ids = serializer.validated_data.get("skill_ids_json", [])
            project = serializer.save(created_by=user, updated_by=user)
            if images_data:
                for image_data in images_data:
                    ProjectImage.objects.create(project=project, image=image_data)
            _replace_links(project, links)
            _replace_skills(project, skill_ids)
            read_serializer = ProjectSerializer(project)
            return CustomResponse(
                response={"Project": read_serializer.data}
            ).get_success_response()
        else:
            print(serializer.errors)
            return CustomResponse(general_message=serializer.errors).get_failure_response()

    
class ProjectMemberAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Projects'],
        description="Retrieve Project Member.",
        responses={200: ProjectMemberSerializer},
    )
    def get(self, request, project_id):
        members = (ProjectMember.objects.filter(project_id=project_id)
                   .select_related("user"))
        return CustomResponse(
            response={"Members": ProjectMemberSerializer(members, many=True).data}
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Projects'],
        description="Create Project Member.",
        request=AddMemberSerializer,
        responses={200: ProjectMemberSerializer},
    )
    def post(self, request, project_id):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return CustomResponse(general_message="project not found").get_failure_response()
        if project.created_by_id != user.id:
            return CustomResponse(general_message="only the project owner can add members").get_failure_response()

        serializer = AddMemberSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(general_message=serializer.errors).get_failure_response()

        resolved_user = serializer.validated_data["resolved_user"]
        external_name = serializer.validated_data.get("external_name") or None
        role = serializer.validated_data.get("role") or None

        if resolved_user and ProjectMember.objects.filter(project=project, user=resolved_user).exists():
            return CustomResponse(general_message="user is already a member").get_failure_response()

        member = ProjectMember.objects.create(
            project=project,
            user=resolved_user,
            external_name=external_name if not resolved_user else None,
            role=role,
            created_by=user,
        )
        return CustomResponse(
            response={"Member": ProjectMemberSerializer(member).data}
        ).get_success_response()

    @extend_schema(tags=['Dashboard - Projects'], description="Delete Project Member.",
        responses={200: ProjectMemberSerializer},
    )
    def delete(self, request, project_id, pk):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return CustomResponse(general_message="project not found").get_failure_response()
        if project.created_by_id != user.id:
            return CustomResponse(general_message="only the project owner can remove members").get_failure_response()
        try:
            member = ProjectMember.objects.get(id=pk, project_id=project_id)
        except ProjectMember.DoesNotExist:
            return CustomResponse(general_message="member not found").get_failure_response()
        member.delete()
        return CustomResponse(general_message="Member removed").get_success_response()


class ProjectVoteAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Projects'],
        description="Create Project Vote.",
        responses={200: VoteSerializer},
    )
    def post(self, request):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))
        project_id = request.data.get("project")
        vote_value = request.data.get("vote")
        if vote_value not in ("upvote", "downvote"):
            return CustomResponse(general_message="invalid vote value").get_failure_response()
        vote, _ = Vote.objects.update_or_create(
            project_id=project_id, user=user,
            defaults={"vote": vote_value, "created_by": user, "updated_by": user},
        )
        return CustomResponse(response={"Vote": VoteSerializer(vote).data}).get_success_response()

    @extend_schema(tags=['Dashboard - Projects'], description="Delete Project Vote.",
        responses={200: VoteSerializer},
    )
    def delete(self, request, pk):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))
        try:
            Vote.objects.get(id=pk, user=user).delete()
        except Vote.DoesNotExist:
            return CustomResponse(general_message="vote not found").get_failure_response()
        return CustomResponse(general_message="Vote deleted successfully").get_success_response()


class ProjectCommentAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Projects'],
        description="Create Project Comment.",
        request=CommentSerializer,
        responses={200: CommentSerializer},
    )
    def post(self, request):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))
        data = {"comment": request.data.get("comment"), "project": request.data.get("project")}
        serializer = CommentSerializer(data=data)
        if serializer.is_valid():
            comment = serializer.save(user=user, created_by=user, updated_by=user)
            return CustomResponse(response={"Comment": CommentSerializer(comment).data}).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @extend_schema(tags=['Dashboard - Projects'], description="Update Project Comment.",
        responses={200: CommentSerializer},
    )
    def put(self, request, pk):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))
        try:
            comment = Comment.objects.get(id=pk, user=user)
        except Comment.DoesNotExist:
            return CustomResponse(general_message="comment not found or not owned").get_failure_response()
        serializer = CommentSerializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=user)
            return CustomResponse(response={"Comment": serializer.data}).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()

    @extend_schema(tags=['Dashboard - Projects'], description="Delete Project Comment.",
        responses={200: CommentSerializer},
    )
    def delete(self, request, pk):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))
        try:
            Comment.objects.get(id=pk, user=user).delete()
        except Comment.DoesNotExist:
            return CustomResponse(general_message="comment not found or not owned").get_failure_response()
        return CustomResponse(general_message="comment deleted successfully").get_success_response()