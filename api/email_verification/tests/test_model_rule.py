"""Spec A §3.1: a changed email is never verified. DB-free: Model.save is patched."""
from datetime import datetime, timezone as dt_timezone
from unittest import mock

import pytest
from django.db import models

from db.signals import user_email_changed
from db.user import User

FIELDS = [field.attname for field in User._meta.concrete_fields]
VERIFIED_AT = datetime(2026, 10, 1, 9, 30, tzinfo=dt_timezone.utc)


def loaded_user(email="asha@example.com", verified=True):
    row = dict.fromkeys(FIELDS)
    row.update(
        id="u-1", muid="asha@mulearn", full_name="Asha Nair", email=email,
        admin=False, exist_in_guild=False,
        interested_in_work=False, interested_in_gig_work=False,
    )
    if verified:
        row.update(email_verified_at=VERIFIED_AT, email_verified_via="signup")
    return User.from_db("default", FIELDS, [row[name] for name in FIELDS])


@pytest.fixture
def db_save():
    with mock.patch.object(models.Model, "save", autospec=True) as save:
        yield save


@pytest.fixture
def changes():
    received = []

    def handler(sender, user, old_email, new_email, old_was_verified, verified_via, **kwargs):
        received.append((user.pk, old_email, new_email, old_was_verified, verified_via))

    user_email_changed.connect(handler, weak=False, dispatch_uid="test-model-rule")
    yield received
    user_email_changed.disconnect(dispatch_uid="test-model-rule")


def test_changed_email_drops_verification_and_announces_it(db_save, changes):
    user = loaded_user()
    user.email = "asha.new@example.com"
    user.save()
    assert user.email_verified_at is None
    assert user.email_verified_via is None
    assert changes == [("u-1", "asha@example.com", "asha.new@example.com", True, None)]


def test_case_only_edit_is_not_a_change(db_save, changes):
    user = loaded_user(email="Asha@Example.com")
    user.email = "asha@example.com"
    user.save()
    assert user.email_verified_at == VERIFIED_AT
    assert changes == []


def test_verified_change_keeps_the_new_proof(db_save, changes):
    user = loaded_user()
    user.email = "asha.new@example.com"
    user.mark_email_verified_on_save("email_change")
    user.save()
    assert user.email_verified_at is not None
    assert user.email_verified_via == "email_change"
    assert changes == [("u-1", "asha@example.com", "asha.new@example.com", True, "email_change")]


def test_unrelated_save_leaves_verification_alone(db_save, changes):
    user = loaded_user()
    user.full_name = "Asha N"
    user.save()
    assert user.email_verified_via == "signup"
    assert changes == []


def test_update_fields_without_email_skips_the_rule(db_save, changes):
    user = loaded_user()
    user.email = "asha.new@example.com"
    user.save(update_fields=["full_name"])
    assert user.email_verified_via == "signup"
    assert changes == []


def test_update_fields_with_email_also_writes_the_verification_columns(db_save, changes):
    user = loaded_user()
    user.email = "asha.new@example.com"
    user.save(update_fields=["email"])
    assert db_save.call_args.kwargs["update_fields"] == {"email", "email_verified_at", "email_verified_via"}


def test_new_user_is_not_a_change(db_save, changes):
    User(id="u-2", muid="x@mulearn", full_name="X", email="x@example.com").save()
    assert changes == []


def test_unknown_loaded_email_falls_back_to_the_database(db_save, changes):
    user = loaded_user()
    user._loaded_email = None  # e.g. the row was loaded with the email deferred
    user.email = "asha.new@example.com"
    lookup = mock.Mock()
    lookup.values_list.return_value.first.return_value = ("asha@example.com", VERIFIED_AT)
    with mock.patch.object(User.every, "filter", return_value=lookup):
        user.save()
    assert user.email_verified_at is None
    assert changes == [("u-1", "asha@example.com", "asha.new@example.com", True, None)]


def test_saving_again_after_a_change_is_quiet(db_save, changes):
    user = loaded_user()
    user.email = "asha.new@example.com"
    user.save()
    user.save()
    assert len(changes) == 1


def test_refresh_from_db_moves_the_baseline(db_save, changes):
    user = loaded_user()

    def fake_refresh(self, using=None, fields=None):
        self.email = "changed.elsewhere@example.com"  # written by another process
        self.email_verified_at = None

    with mock.patch.object(models.Model, "refresh_from_db", fake_refresh):
        user.refresh_from_db()
    user.save()
    assert changes == []
