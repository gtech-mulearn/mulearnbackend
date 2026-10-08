import uuid

from django.db import models


class ProblemStatement(models.Model):
    class Status(models.TextChoices):
        DRAFT = "Draft"
        PUBLISHED = "Published"
        UNPUBLISHED = "Unpublished"

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='problem_statements')
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(max_length=100)
    skills = models.JSONField(default=list)
    deadline = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE, db_column='created_by',
                                   related_name='problem_statements_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey('User', on_delete=models.CASCADE, db_column='updated_by',
                                   related_name='problem_statements_updated')
    updated_at = models.DateTimeField(auto_now=True)
    published_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True,
                                     db_column='published_by', related_name='problem_statements_published')
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'problem_statement'


class ProblemStatementInteraction(models.Model):
    class Status(models.TextChoices):
        TRYING = "Trying"

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    problem_statement = models.ForeignKey(ProblemStatement, on_delete=models.CASCADE,
                                          related_name='interactions')
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='problem_statement_interactions')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRYING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'problem_statement_interaction'
        unique_together = (('problem_statement', 'user'),)
