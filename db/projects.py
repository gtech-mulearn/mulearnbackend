import uuid

from django.db import models
from db.user import User
from db.skill import Skill


class Project(models.Model):
    STATUS_CHOICES = [("draft", "Draft"), ("published", "Published"), ("archived", "Archived")]
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    logo = models.ImageField(upload_to="projects/logos/", null=True, blank=True)
    title = models.CharField(max_length=50)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="published")
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="created_projects", db_column="created_by",
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="updated_projects", db_column="updated_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "projects"
        ordering = ["-created_at"]


class ProjectImage(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    project = models.ForeignKey(Project, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="projects/images/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "project_images"


class ProjectLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    project = models.ForeignKey(Project, related_name="links", on_delete=models.CASCADE)
    label = models.CharField(max_length=50)
    url = models.CharField(max_length=500)
    position = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "project_links"
        ordering = ["position", "created_at"]


class ProjectSkillLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    project = models.ForeignKey(Project, related_name="skill_links", on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "project_skill_link"
        unique_together = ("project", "skill")


class Comment(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    comment = models.TextField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="project_comments", db_column="user_id",
    )
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="created_project_comments", db_column="created_by",
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="updated_project_comments", db_column="updated_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "projects_comments"
        ordering = ["created_at"]


class Vote(models.Model):
    VOTE_CHOICES = [("upvote", "Upvote"), ("downvote", "Downvote")]
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    vote = models.CharField(max_length=10, choices=VOTE_CHOICES)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="project_votes", db_column="user_id",
    )
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="created_project_votes", db_column="created_by",
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="updated_project_votes", db_column="updated_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "projects_votes"
        ordering = ["created_at"]
        unique_together = ("user", "project")


class ProjectMember(models.Model):
    """Unified team member: either `user` (linked mulearn user) or
    `external_name` (plain text) is set. Enforced at DB level via CHECK constraint."""
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="project_memberships", db_column="user_id",
        null=True, blank=True,
    )
    external_name = models.CharField(max_length=100, null=True, blank=True)
    role = models.CharField(max_length=50, null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name="created_project_members", db_column="created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "project_members"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                check=(
                    (models.Q(user__isnull=False) & models.Q(external_name__isnull=True)) |
                    (models.Q(user__isnull=True)  & models.Q(external_name__isnull=False))
                ),
                name="chk_project_member_identity",
            ),
        ]
        unique_together = ("user", "project")
