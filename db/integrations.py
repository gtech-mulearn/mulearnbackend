import uuid

from django.db import models

from db.user import User


class Integration(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    name = models.CharField(max_length=255, null=False)
    token = models.CharField(max_length=400, null=False)
    auth_token = models.CharField(max_length=255, null=False)
    base_url = models.CharField(max_length=255, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration"


#
class IntegrationAuthorization(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    integration = models.ForeignKey(
        Integration,
        on_delete=models.CASCADE,
        null=False,
        related_name="integration_authorization_integration",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="integration_authorization_user",
        null=False,
    )
    integration_value = models.CharField(max_length=255, unique=True, null=False)
    additional_field = models.CharField(max_length=255)
    verified = models.BooleanField(default=False, null=False)
    updated_at = models.DateTimeField(null=False, auto_now=True)
    created_at = models.DateTimeField(null=False, auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["integration_id", "user_id", "integration_value"],
                name="unique_integration_per_user",
            ),
        ]
        db_table = "integration_authorization"
