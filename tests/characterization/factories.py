"""factory_boy factories for characterization tests: the smallest valid rows, nothing more.

Audit columns (created_by, updated_by) point at the system user, which the MySQL tier keeps in
place (the root conftest).
"""

import uuid

import factory
from django.conf import settings

from db.task import Wallet
from db.user import Role, User, UserRoleLink


def system_user_id():
    return settings.SYSTEM_ADMIN_ID


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    muid = factory.Sequence(lambda n: f"characterization-{n}@mulearn")
    full_name = factory.Sequence(lambda n: f"Characterization User {n}")
    email = factory.Sequence(lambda n: f"characterization-{n}@example.com")


class WalletFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Wallet

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user = factory.SubFactory(UserFactory)
    created_by_id = factory.LazyFunction(system_user_id)
    updated_by_id = factory.LazyFunction(system_user_id)


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Role
        django_get_or_create = ("title",)

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    title = "Student"
    created_by_id = factory.LazyFunction(system_user_id)
    updated_by_id = factory.LazyFunction(system_user_id)


class UserRoleLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserRoleLink

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user = factory.SubFactory(UserFactory)
    role = factory.SubFactory(RoleFactory)
    verified = True
    created_by_id = factory.LazyFunction(system_user_id)
