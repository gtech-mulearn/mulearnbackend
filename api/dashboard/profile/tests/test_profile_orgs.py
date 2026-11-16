"""UserProfileSerializer's college_* / company_* fields.

college_* used to switch to the company for anyone with the Mentor role, so
a mentor's college_id was a company id ("campus not found" when opened as a
campus) and a Student who was also a Mentor lost their college.
DB-free: the prefetched links are plain objects.
"""
from datetime import datetime
from types import SimpleNamespace

from api.dashboard.profile.profile_serializer import UserProfileSerializer
from utils.types import OrganizationType


def _link(org_type, org_id, *, code=None, title=None, district="d1", day=1):
    org = SimpleNamespace(
        id=org_id, org_type=org_type, code=code, title=title, district_id=district
    )
    return SimpleNamespace(org=org, created_at=datetime(2026, 1, day), id=org_id)


def _user(*links):
    return SimpleNamespace(
        user_organization_link_user=SimpleNamespace(all=lambda: list(links))
    )


COLLEGE = OrganizationType.COLLEGE.value
COMPANY = OrganizationType.COMPANY.value


def _fields(user):
    s = UserProfileSerializer()
    return {
        "college_id": s.get_college_id(user),
        "college_code": s.get_college_code(user),
        "company_id": s.get_company_id(user),
        "company_name": s.get_company_name(user),
        "org_district_id": s.get_org_district_id(user),
    }


def test_a_mentor_at_a_company_has_no_college_id():
    user = _user(_link(COMPANY, "acme", title="Acme", district="d9"))
    assert _fields(user) == {
        "college_id": None,
        "college_code": None,
        "company_id": "acme",
        "company_name": "Acme",
        "org_district_id": "d9",
    }


def test_a_student_mentor_keeps_both():
    user = _user(
        _link(COLLEGE, "cet", code="CET", district="d1"),
        _link(COMPANY, "acme", title="Acme", district="d9"),
    )
    assert _fields(user) == {
        "college_id": "cet",
        "college_code": "CET",
        "company_id": "acme",
        "company_name": "Acme",
        "org_district_id": "d1",
    }


def test_the_newest_college_link_wins():
    user = _user(
        _link(COLLEGE, "old", code="OLD", day=1),
        _link(COLLEGE, "new", code="NEW", day=5),
    )
    assert _fields(user)["college_code"] == "NEW"


def test_no_links_means_nothing():
    assert set(_fields(_user()).values()) == {None}


def test_one_serializer_never_mixes_two_users():
    """Under many=True one serializer instance serves every row."""
    s = UserProfileSerializer()
    a = _user(_link(COLLEGE, "cet", code="CET"))
    b = _user(_link(COLLEGE, "gec", code="GEC"))
    assert (s.get_college_code(a), s.get_college_code(b)) == ("CET", "GEC")
