import uuid

from django.db import models

from db.user import User

from django.conf import settings

# fmt: off
# noinspection PyPep8

class Integration(models.Model):
    id                = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    name              = models.CharField(max_length=255, null=False)
    token             = models.CharField(max_length=400, null=False)
    auth_token        = models.CharField(max_length=255, null=False)
    base_url          = models.CharField(max_length=255, null=False)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration"



class IntegrationAuthorization(models.Model):
    id                = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4)
    integration       = models.ForeignKey(Integration, on_delete=models.CASCADE, null=False, related_name="integration_authorization_integration",)
    user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name="integration_authorization_user", null=False,)
    integration_value = models.CharField(max_length=255, unique=True, null=False)
    additional_field  = models.CharField(max_length=255)
    verified          = models.BooleanField(default=False, null=False)
    updated_at        = models.DateTimeField(null=False, auto_now=True)
    created_at        = models.DateTimeField(null=False, auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["integration_id", "user_id", "integration_value"],
                name="unique_integration_per_user",
            ),
        ]
        db_table = "integration_authorization"


class IntegrationAccountLink(models.Model):
    """
    One µLearn account-holder (user, company or college) linked to one
    partner account (spec B §3.2). Provider-agnostic; Futuremug is first.
    The partner exposes no account id, so external_email is the identity.
    """
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    provider = models.CharField(max_length=30)
    account_type = models.CharField(max_length=20)
    subject_type = models.CharField(max_length=20)  # user | company | organization
    subject_id = models.CharField(max_length=36)
    contact_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column="contact_user_id",
                                     related_name="integration_account_links_as_contact")
    status = models.CharField(max_length=20)  # consented | active | pending_approval | blocked | rejected | disconnected
    external_email = models.CharField(max_length=60, null=True, blank=True)
    synced_first_name = models.CharField(max_length=25, null=True, blank=True)
    synced_last_name = models.CharField(max_length=25, null=True, blank=True)
    synced_phone = models.CharField(max_length=15, null=True, blank=True)
    consent_version = models.CharField(max_length=30, null=True, blank=True)
    consented_at = models.DateTimeField(null=True, blank=True)
    consented_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column="consented_by",
                                     related_name="integration_account_links_consented")
    disconnected_at = models.DateTimeField(null=True, blank=True)
    disconnected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column="disconnected_by",
                                        related_name="integration_account_links_disconnected")
    last_login_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "integration_account_link"


class IntegrationAccountEvent(models.Model):
    """Append-only audit of a link (spec B §3.2): never values, URLs or secrets."""
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    link = models.ForeignKey(IntegrationAccountLink, on_delete=models.CASCADE, db_column="link_id", related_name="events")
    event = models.CharField(max_length=30)
    actor_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column="actor_user_id",
                                   related_name="integration_account_events")
    consent_version = models.CharField(max_length=30, null=True, blank=True)
    details = models.JSONField(null=True, blank=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "integration_account_event"
