"""The MySQL tier runs against test_mulearn as loaded from schema/latest.sql (issue 0012)."""

import os

import pytest
from django.db import connection

pytestmark = [pytest.mark.mysql, pytest.mark.django_db]


def test_the_schema_tables_exist():
    tables = set(connection.introspection.table_names())

    assert {"user", "wallet", "karma_activity_log"} <= tables


def test_tests_use_the_loaded_database_not_a_created_copy():
    # pytest-django would otherwise create an empty test_<name> database and run there.
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE()")
        (name,) = cursor.fetchone()

    assert name == os.environ["DATABASE_NAME"]
