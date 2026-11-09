from types import SimpleNamespace
from unittest import mock

from django.db.models.signals import post_delete

from api.integrations.partner_sso import signals


def test_cleanup_receivers_are_registered_at_startup():
    uids = {entry[0][0] for entry in post_delete.receivers}
    assert {"partner_sso.cleanup_user", "partner_sso.cleanup_company", "partner_sso.cleanup_organization"} <= uids


def test_deleting_a_subject_deletes_its_links():
    with mock.patch.object(signals.IntegrationAccountLink.objects, "filter") as links:
        signals.on_company_deleted(sender=None, instance=SimpleNamespace(id="c-1"))
    links.assert_called_once_with(subject_type="company", subject_id="c-1")
    links.return_value.delete.assert_called_once_with()
