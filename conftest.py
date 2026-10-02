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
        pass

