"""The system user survives transactional tests (issue 0012).

The backend refuses to start without the user whose id is SYSTEM_ADMIN_ID (db/apps.py). A
transaction=True test commits, so whatever it deletes stays deleted. The root conftest puts
the system user back before each mysql test and when the session ends.
"""

import pytest
from django.conf import settings
from django.db import connection

pytestmark = pytest.mark.mysql


def system_user_exists():
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM user WHERE id = %s", [settings.SYSTEM_ADMIN_ID])
        return cursor.fetchone()[0] == 1


# Both tests are transactional: pytest-django runs non-transactional tests first, so this
# keeps them in file order.
@pytest.mark.django_db(transaction=True)
def test_a_transactional_test_may_delete_the_system_user():
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM user WHERE id = %s", [settings.SYSTEM_ADMIN_ID])

    assert not system_user_exists()


@pytest.mark.django_db(transaction=True)
def test_the_next_mysql_test_still_finds_the_system_user():
    assert system_user_exists()
