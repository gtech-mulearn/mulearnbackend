import uuid

from django.db import models
from django.conf import settings

from .user import User
from .task import TaskList


class Skill(models.Model):
    """
    Skill model for categorizing tasks.
    Skills can be used to create skill-based achievements.
    """
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name = models.CharField(max_length=75, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column="updated_by",
        related_name="skill_updated_by",
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column="created_by",
        related_name="skill_created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "skill"

    def __str__(self):
        return self.name


class TaskSkillLink(models.Model):
    """
    Junction table linking tasks to skills (many-to-many).
    A task can have multiple skills, and a skill can be associated with multiple tasks.
    """
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    task = models.ForeignKey(
        TaskList,
        on_delete=models.CASCADE,
        related_name="skill_links",
        db_column="task_id",
    )
    skill = models.ForeignKey(
        "Skill",
        on_delete=models.CASCADE,
        related_name="task_links",
        db_column="skill_id",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column="created_by",
        related_name="task_skill_link_created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "task_skill_link"
        unique_together = [["task", "skill"]]

    def __str__(self):
        return f"{self.task.title} - {self.skill.name}"
