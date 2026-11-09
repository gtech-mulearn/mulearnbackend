from unittest import mock

import pytest
from django.test import override_settings

from api.integrations.futuremug import adapter as adapter_module
from api.integrations.futuremug.adapter import FuturemugAdapter
from api.integrations.partner_sso.adapter import Contact

ON = {"FUTUREMUG_API_KEY": "k", "FUTUREMUG_BASE_URL": "https://newdev.futuremug.com",
      "FUTUREMUG_TERMS_URL": "https://t", "FUTUREMUG_PRIVACY_URL": "https://p"}


@pytest.fixture(autouse=True)
def flag_on():
    # The admin switch (System → Features); test_feature_flag.py covers the flag itself.
    with mock.patch.object(adapter_module, "is_flag_on", return_value=True) as flag:
        yield flag


def test_enabled_only_with_switch_key_https_and_legal_links():
    with override_settings(**ON):
        assert FuturemugAdapter().is_enabled()


def test_the_switch_off_disables_it(flag_on):
    flag_on.return_value = False
    with override_settings(**ON):
        assert FuturemugAdapter().is_configured()
        assert not FuturemugAdapter().is_enabled()


@pytest.mark.parametrize("override", [
    {"FUTUREMUG_API_KEY": ""}, {"FUTUREMUG_BASE_URL": "http://newdev.futuremug.com"},
    {"FUTUREMUG_TERMS_URL": ""}, {"FUTUREMUG_PRIVACY_URL": ""},
])
def test_anything_missing_disables_it(override):
    with override_settings(**{**ON, **override}):
        assert not FuturemugAdapter().is_enabled()


def test_open_session_maps_the_partner_reply():
    adapter = FuturemugAdapter()
    contact = Contact(email="asha@example.com", first_name="Asha", last_name=None, phone=None, organization_name=None)
    client = mock.Mock()
    client.session.return_value = {"success": True, "status": "login", "login_url": "https://newdev.futuremug.com/x",
                                   "expires_in": 120, "account_created": False}
    with override_settings(**ON), mock.patch.object(adapter, "_client", return_value=client):
        result = adapter.open_session("candidate", contact)
    client.session.assert_called_once_with({"account_type": "candidate", "email": "asha@example.com", "first_name": "Asha"})
    assert (result.status, result.expires_in, result.account_created) == ("login", 120, False)


def test_a_key_with_a_trailing_newline_is_trimmed():
    # Common when the env var comes from a secret file.
    with override_settings(**{**ON, "FUTUREMUG_API_KEY": "fmsso_key\n"}):
        adapter = FuturemugAdapter()
        assert adapter.is_enabled()
        assert adapter._client()._api_key == "fmsso_key"


@pytest.mark.parametrize("key", ["fmsso key", "fmsso\rkey", "fmsso_kéy"])
def test_a_malformed_key_keeps_it_disabled_without_logging_the_key(key, caplog):
    with override_settings(**{**ON, "FUTUREMUG_API_KEY": key}):
        assert not FuturemugAdapter().is_enabled()
    assert key not in caplog.text
    assert "FUTUREMUG_API_KEY" in caplog.text  # ops still get a signal
