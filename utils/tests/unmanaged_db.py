"""Shared helpers for tests that need real tables for managed=False models.

Run ONLY with the in-memory SQLite environment (see test_push_db.py); the
class refuses to touch any other database.
"""
from datetime import timedelta

import jwt
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from db.user import Role, User, UserRoleLink


def with_dependencies(models: list) -> list:
    """Models plus every model they reference through forward FKs, in an
    order where each table is created after the tables it points at."""
    ordered, seen = [], set()

    def visit(model):
        if model in seen:
            return
        seen.add(model)
        for f in model._meta.fields:
            target = getattr(f, "related_model", None)
            if f.is_relation and target and target is not model:
                visit(target)
        ordered.append(model)

    for m in models:
        visit(m)
    return ordered


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class UnmanagedDbTestCase(TransactionTestCase):
    MODELS: list = []
    _tables: list = []

    @classmethod
    def setUpClass(cls):
        assert "sqlite" in settings.DATABASES["default"]["ENGINE"], (
            "run with the in-memory SQLite env"
        )
        super().setUpClass()
        cls._tables = with_dependencies(cls.MODELS)
        with connection.schema_editor() as editor:
            for model in cls._tables:
                editor.create_model(model)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            for model in reversed(cls._tables):
                editor.delete_model(model)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        # TransactionTestCase's flush skips managed=False tables. Plain SQL: an
        # ORM delete() would follow cascades into tables not created here.
        with connection.cursor() as cursor:
            for model in reversed(self._tables):
                cursor.execute(f'DELETE FROM "{model._meta.db_table}"')
        cache.clear()


def make_user(user_id: str, verified: dict[str, bool] | None = None) -> User:
    """A user plus one role link per {title: verified} entry."""
    user = User.objects.create(
        id=user_id,
        full_name=user_id,
        email=f"{user_id}@test.invalid",
        muid=f"{user_id}@mulearn",
    )
    for title, is_verified in (verified or {}).items():
        role = Role.objects.filter(title=title).first() or Role.objects.create(
            id=f"role-{title}", title=title, updated_by=user, created_by=user
        )
        UserRoleLink.objects.create(
            user=user, role=role, verified=is_verified, created_by=user
        )
    return user


def bearer(user_id: str, roles: list[str]) -> str:
    """Authorization header value carrying a real signed JWT."""
    expiry = (timezone.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S%z")
    token = jwt.encode(
        {"id": user_id, "expiry": expiry, "roles": list(roles)},
        settings.SECRET_KEY,
        algorithm="HS256",
    )
    return f"Bearer {token}"
