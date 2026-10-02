"""Root pytest conftest.

The db.* models are all `managed = False` and the project ships no migrations,
so Django has to be set up explicitly before any test module imports a model.
"""
import os
import pymysql
pymysql.version_info = (1, 4, 6, 'final', 0)
pymysql.install_as_MySQLdb()

import pytest
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mulearnbackend.settings")
django.setup()


@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    """Bypass test database creation/destruction since mudev user lacks CREATE DATABASE privileges."""
    with django_db_blocker.unblock():
        from django.db import connection
        with connection.cursor() as cursor:
            cols = {
                'work_link': "ALTER TABLE problem_statement_interest ADD COLUMN work_link VARCHAR(500) NULL AFTER note",
                'status_updated_by': "ALTER TABLE problem_statement_interest ADD COLUMN status_updated_by VARCHAR(36) NULL",
                'status_updated_at': "ALTER TABLE problem_statement_interest ADD COLUMN status_updated_at DATETIME NULL",
                'expressed_at': "ALTER TABLE problem_statement_interest ADD COLUMN expressed_at DATETIME NULL",
            }
            for col_name, sql in cols.items():
                cursor.execute(f"SHOW COLUMNS FROM problem_statement_interest LIKE '{col_name}'")
                if not cursor.fetchone():
                    cursor.execute(sql)

