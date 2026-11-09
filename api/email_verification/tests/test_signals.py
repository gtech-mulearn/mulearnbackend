"""Spec A §3.7: an email change revokes old-inbox secrets and warns the old inbox."""
from types import SimpleNamespace
from unittest import mock

from api.email_verification import signals
from api.email_verification.signals import handle_email_changed  # the real one
from db.signals import user_email_changed

USER = SimpleNamespace(id="u-1", email="new@example.com")


def run_now(func):
    func()


def patched(mail=None):
    return (
        mock.patch.object(signals.ForgotPassword.objects, "filter"),
        mock.patch.object(signals.OtpVerification.objects, "filter"),
        mock.patch.object(signals.transaction, "on_commit", run_now),
        mock.patch.object(signals, "send_template_mail", mail or mock.Mock()),
    )


def test_revokes_reset_links_and_login_otps():
    resets_patch, otps_patch, commit_patch, mail_patch = patched()
    with resets_patch as resets, otps_patch as otps, commit_patch, mail_patch:
        handle_email_changed(user=USER, old_email="old@example.com", old_was_verified=False)
    resets.assert_called_once_with(user_id="u-1")
    resets.return_value.delete.assert_called_once_with()
    otps.assert_called_once_with(user_id="u-1")
    otps.return_value.delete.assert_called_once_with()


def test_notifies_a_verified_old_address_with_the_new_one_masked():
    mail = mock.Mock()
    resets_patch, otps_patch, commit_patch, mail_patch = patched(mail)
    with resets_patch, otps_patch, commit_patch, mail_patch:
        handle_email_changed(user=USER, old_email="old@example.com", old_was_verified=True)
    context = mail.call_args.kwargs["context"]
    assert context["email"] == "old@example.com"
    assert context["new_email_masked"] == "n•••@example.com"
    assert mail.call_args.kwargs["address"] == ["email_verification", "email_changed.html"]


def test_does_not_mail_an_old_address_that_was_never_verified():
    mail = mock.Mock()
    resets_patch, otps_patch, commit_patch, mail_patch = patched(mail)
    with resets_patch, otps_patch, commit_patch, mail_patch:
        handle_email_changed(user=USER, old_email="old@example.com", old_was_verified=False)
    mail.assert_not_called()


def test_a_failed_notice_is_logged_not_raised():
    mail = mock.Mock(side_effect=ConnectionError("smtp down"))
    resets_patch, otps_patch, commit_patch, mail_patch = patched(mail)
    with resets_patch, otps_patch, commit_patch, mail_patch, mock.patch.object(signals, "logger") as logger:
        handle_email_changed(user=USER, old_email="old@example.com", old_was_verified=True)
    logger.exception.assert_called_once()


def test_the_receiver_is_registered_at_startup():
    assert any(entry[0][0] == "email_verification.on_user_email_changed"
               for entry in user_email_changed.receivers)


def test_codes_still_bound_for_the_old_address_are_revoked():
    from django.core.cache import cache
    from django.test import override_settings

    from api.email_verification import codes

    locmem = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "email-signals"}}
    with override_settings(CACHES=locmem):
        cache.clear()
        for purpose in ("account", "change"):
            cache.set(codes._code_key(purpose, "u-1"), {"email": "old@example.com"}, 600)
        cache.set(codes._code_key("account", "u-2"), {"email": "someone@example.com"}, 600)
        resets_patch, otps_patch, commit_patch, mail_patch = patched()
        with resets_patch, otps_patch, commit_patch, mail_patch:
            handle_email_changed(user=USER, old_email="old@example.com", old_was_verified=False)
        assert cache.get(codes._code_key("account", "u-1")) is None
        assert cache.get(codes._code_key("change", "u-1")) is None
        assert cache.get(codes._code_key("account", "u-2")) is not None
        cache.clear()
