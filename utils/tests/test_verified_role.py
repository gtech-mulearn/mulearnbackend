"""verified_role_required: the token's roles AND a verified database link must agree."""
from rest_framework.test import APIRequestFactory

from db.user import Role, User, UserRoleLink
from utils.permission import (
    invalidate_verified_roles,
    verified_role_required,
    verified_role_titles,
)
from utils.response import CustomResponse
from utils.tests.unmanaged_db import UnmanagedDbTestCase, bearer, make_user
from utils.types import TEAM_ROLES


class _DummyView:
    @verified_role_required(TEAM_ROLES)
    def get(self, request):
        return CustomResponse(general_message="ok").get_success_response()


def call(user, roles):
    request = APIRequestFactory().get("/x", HTTP_AUTHORIZATION=bearer(user, roles))
    return _DummyView().get(request)


class VerifiedRoleTests(UnmanagedDbTestCase):
    MODELS = [User, Role, UserRoleLink]

    def test_verified_fellow_passes(self):
        make_user("f1", {"Fellow": True})
        assert call(user="f1", roles=["Fellow"]).data["hasError"] is False

    def test_token_fellow_but_only_student_verified_is_rejected(self):
        make_user("f2", {"Fellow": False, "Student": True})
        r = call(user="f2", roles=["Fellow", "Student"])
        assert r.data["hasError"] is True and r.status_code == 400

    def test_db_verified_fellow_without_token_role_is_rejected(self):
        make_user("f3", {"Fellow": True})
        assert call(user="f3", roles=["Student"]).data["hasError"] is True

    def test_unverified_admin_is_rejected(self):
        make_user("a1", {"Admins": False})
        assert call(user="a1", roles=["Admins"]).data["hasError"] is True

    def test_verified_titles_are_cached_until_invalidated(self):
        make_user("f4", {"Fellow": True})
        assert verified_role_titles("f4") == frozenset({"Fellow"})
        UserRoleLink.objects.filter(user_id="f4").update(verified=False)
        assert verified_role_titles("f4") == frozenset({"Fellow"})
        invalidate_verified_roles("f4")
        assert verified_role_titles("f4") == frozenset()

    def test_inactive_verified_link_is_rejected(self):
        make_user("f5", {"Fellow": True})
        UserRoleLink.objects.filter(user_id="f5").update(is_active=False)
        assert call(user="f5", roles=["Fellow"]).data["hasError"] is True
