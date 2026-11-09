"""Remove partner links when their µLearn subject is deleted (spec B §3.2).
subject_id spans three tables, so it cannot be a foreign key."""
from django.db.models.signals import post_delete
from django.dispatch import receiver

from db.company import Company
from db.integrations import IntegrationAccountLink
from db.organization import Organization
from db.user import User


def _delete_links(subject_type, subject_id):
    IntegrationAccountLink.objects.filter(subject_type=subject_type, subject_id=subject_id).delete()


@receiver(post_delete, sender=User, dispatch_uid="partner_sso.cleanup_user")
def on_user_deleted(sender, instance, **kwargs):
    _delete_links("user", instance.id)


@receiver(post_delete, sender=Company, dispatch_uid="partner_sso.cleanup_company")
def on_company_deleted(sender, instance, **kwargs):
    _delete_links("company", instance.id)


@receiver(post_delete, sender=Organization, dispatch_uid="partner_sso.cleanup_organization")
def on_organization_deleted(sender, instance, **kwargs):
    _delete_links("organization", instance.id)
