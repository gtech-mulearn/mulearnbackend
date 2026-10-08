from datetime import timedelta

import jwt
import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from db.company import Company
from db.problem_statement import ProblemStatement, ProblemStatementInteraction
from db.user import User
from utils.types import RoleType

BASE = "/api/v1/dashboard/problem-statements/"

PAYLOAD = {
    "title": "Reduce food waste",
    "description": "Build a system that predicts daily canteen demand.",
    "category": "Sustainability",
    "skills": ["Python", "python", "ML"],
}


def make_user(uid):
    uid = f"pstest_{uid}"  # never collides with real users when run against a shared DB
    return User.objects.create(id=uid, full_name=uid, email=f"{uid}@pstest.invalid", muid=f"{uid}@mulearn")


def client_for(user, roles=()):
    """Client with a real signed JWT, so role_required / fetch_user_id run for real."""
    expiry = (timezone.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S%z")
    token = jwt.encode(
        {"id": user.id, "expiry": expiry, "roles": list(roles)}, settings.SECRET_KEY, algorithm="HS256"
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def make_company(owner, name):
    return Company.objects.create(
        company_user=owner, name=f"pstest-{name}", slug=f"pstest-{name.lower()}", description="d", status="verified"
    )


@pytest.fixture
def world(db):
    a_owner, b_owner, learner, admin = (make_user(u) for u in ("a_owner", "b_owner", "learner", "admin"))
    return {
        "company_a": make_company(a_owner, "CompA"),
        "company_b": make_company(b_owner, "CompB"),
        "a": client_for(a_owner, [RoleType.COMPANY.value]),
        "b": client_for(b_owner, [RoleType.COMPANY.value]),
        "learner": client_for(learner),
        "learner_user": learner,
        "admin": client_for(admin, [RoleType.ADMIN.value]),
    }


def create(client, **extra):
    return client.post(BASE + "company/", {**PAYLOAD, **extra}, format="json")


def create_published(world, client_key="a"):
    sid = create(world[client_key]).json()["response"]["id"]
    assert world[client_key].post(f"{BASE}company/{sid}/publish/").status_code == 200
    return sid


# ----------------------------------------------------------------- company

def test_company_creates_draft_and_dedupes_skills(world):
    res = create(world["a"])
    assert res.status_code == 200
    body = res.json()["response"]
    assert body["status"] == "Draft"
    assert body["skills"] == ["Python", "ML"]
    assert body["company"]["id"] == str(world["company_a"].id)


def test_company_cannot_choose_company_in_body(world):
    res = create(world["a"], company_id=str(world["company_b"].id))
    assert res.status_code == 400  # unknown field is rejected
    assert not ProblemStatement.objects.filter(company=world["company_b"]).exists()


def test_company_cannot_touch_other_companys_statement(world):
    sid = create(world["a"]).json()["response"]["id"]
    assert world["b"].get(f"{BASE}company/{sid}/").status_code == 404
    assert world["b"].patch(f"{BASE}company/{sid}/", {"title": "Hijacked!"}, format="json").status_code == 404
    assert world["b"].post(f"{BASE}company/{sid}/publish/").status_code == 404
    assert world["b"].delete(f"{BASE}company/{sid}/").status_code == 404
    assert ProblemStatement.objects.filter(id=sid).exists()


def test_company_list_only_shows_own(world):
    create(world["a"])
    create(world["b"])
    data = world["a"].get(BASE + "company/").json()["response"]["data"]
    assert len(data) == 1 and data[0]["company"]["id"] == str(world["company_a"].id)


def test_company_update_and_delete(world):
    sid = create(world["a"]).json()["response"]["id"]
    res = world["a"].patch(f"{BASE}company/{sid}/", {"title": "A new title"}, format="json")
    assert res.status_code == 200 and res.json()["response"]["title"] == "A new title"
    assert world["a"].delete(f"{BASE}company/{sid}/").status_code == 200
    assert not ProblemStatement.objects.filter(id=sid).exists()


def test_past_deadline_rejected(world):
    past = (timezone.now() - timedelta(days=1)).isoformat()
    assert create(world["a"], deadline=past).status_code == 400


def test_publish_and_unpublish_set_audit_fields(world):
    sid = create_published(world)
    ps = ProblemStatement.objects.get(id=sid)
    assert ps.status == "Published" and ps.published_by_id == world["company_a"].company_user_id
    assert ps.published_at is not None
    assert world["a"].post(f"{BASE}company/{sid}/publish/").status_code == 409  # already published
    assert world["a"].post(f"{BASE}company/{sid}/unpublish/").status_code == 200
    assert ProblemStatement.objects.get(id=sid).status == "Unpublished"


# ----------------------------------------------------------------- authorization

def test_learner_cannot_use_company_or_admin_routes(world):
    sid = create(world["a"]).json()["response"]["id"]
    for method, url in [
        ("get", BASE + "company/"),
        ("post", BASE + "company/"),
        ("get", BASE + "admin/"),
        ("patch", f"{BASE}admin/{sid}/"),
        ("delete", f"{BASE}admin/{sid}/"),
        ("post", f"{BASE}admin/{sid}/publish/"),
    ]:
        res = getattr(world["learner"], method)(url, {} if method != "get" else None, format="json")
        assert res.status_code in (400, 403), (method, url)
        assert res.json()["hasError"] is True
    assert ProblemStatement.objects.get(id=sid).status == "Draft"


def test_company_user_cannot_use_admin_routes(world):
    assert world["a"].get(BASE + "admin/").json()["hasError"] is True


def test_company_routes_need_company_role_and_own_company(world):
    # a company owner whose token lacks the Company role
    no_role = client_for(world["company_a"].company_user)
    assert no_role.get(BASE + "company/").status_code in (400, 403)
    # a co-admin / mentor (accepted link or not) has no company of their own
    assert world["learner"].post(BASE + "company/", PAYLOAD, format="json").status_code in (400, 403)
    with_role_no_company = client_for(world["learner_user"], [RoleType.COMPANY.value])
    assert with_role_no_company.post(BASE + "company/", PAYLOAD, format="json").status_code == 403


def test_unauthenticated_rejected(world):
    assert APIClient().get(BASE).status_code in (401, 403)


# ----------------------------------------------------------------- visibility

def test_learner_sees_only_published(world):
    draft = create(world["a"]).json()["response"]["id"]
    published = create_published(world)
    unpublished = create_published(world)
    world["a"].post(f"{BASE}company/{unpublished}/unpublish/")

    ids = [s["id"] for s in world["learner"].get(BASE).json()["response"]["data"]]
    assert ids == [published]
    assert world["learner"].get(f"{BASE}{published}/").status_code == 200
    assert world["learner"].get(f"{BASE}{draft}/").status_code == 404
    assert world["learner"].get(f"{BASE}{unpublished}/").json()["statusCode"] == 404
    # owner and admin still see non-published states
    assert world["a"].get(f"{BASE}company/{unpublished}/").status_code == 200
    assert world["admin"].get(f"{BASE}admin/{draft}/").status_code == 200


# ----------------------------------------------------------------- interactions

def test_interaction_add_change_remove_and_counts(world):
    sid = create_published(world)
    url = f"{BASE}{sid}/interaction/"
    assert world["learner"].get(url).json()["response"]["status"] is None

    assert world["learner"].put(url, {"status": "Trying"}, format="json").status_code == 200
    assert world["learner"].put(url, {"status": "Trying"}, format="json").status_code == 200  # no duplicate
    assert ProblemStatementInteraction.objects.filter(problem_statement_id=sid).count() == 1
    assert world["learner"].get(url).json()["response"]["status"] == "Trying"
    assert world["learner"].get(f"{url}counts/").json()["response"] == {"Trying": 1}

    detail = world["learner"].get(f"{BASE}{sid}/").json()["response"]
    assert detail["my_interaction"] == "Trying" and detail["interaction_counts"] == {"Trying": 1}

    assert world["learner"].delete(url).status_code == 200
    assert world["learner"].get(f"{url}counts/").json()["response"] == {"Trying": 0}
    assert world["learner"].delete(url).json()["statusCode"] == 404


def test_interaction_rejects_invalid_status_and_unpublished(world):
    sid = create_published(world)
    url = f"{BASE}{sid}/interaction/"
    assert world["learner"].put(url, {"status": "Nope"}, format="json").status_code == 400
    world["a"].post(f"{BASE}company/{sid}/unpublish/")
    assert world["learner"].put(url, {"status": "Trying"}, format="json").json()["statusCode"] == 404


def test_interaction_is_scoped_to_caller_and_ignores_body_user(world):
    sid = create_published(world)
    other = make_user("other")
    res = world["learner"].put(
        f"{BASE}{sid}/interaction/", {"status": "Trying", "user_id": other.id}, format="json"
    )
    assert res.status_code == 400  # a user id in the body is not accepted
    world["learner"].put(f"{BASE}{sid}/interaction/", {"status": "Trying"}, format="json")
    rows = ProblemStatementInteraction.objects.filter(problem_statement_id=sid)
    assert list(rows.values_list("user_id", flat=True)) == [world["learner_user"].id]


# ----------------------------------------------------------------- stats and admin

def test_company_sees_interactions_only_for_own_statement(world):
    sid = create_published(world)
    world["learner"].put(f"{BASE}{sid}/interaction/", {"status": "Trying"}, format="json")
    res = world["a"].get(f"{BASE}company/{sid}/interactions/").json()["response"]
    assert res["counts"] == {"Trying": 1} and res["data"][0]["user_id"] == world["learner_user"].id
    assert world["b"].get(f"{BASE}company/{sid}/interactions/").json()["statusCode"] == 404


def test_admin_has_full_control(world):
    sid = create(world["a"]).json()["response"]["id"]
    admin = world["admin"]

    assert len(admin.get(BASE + "admin/").json()["response"]["data"]) == 1
    assert admin.patch(f"{BASE}admin/{sid}/", {"title": "Admin edit"}, format="json").status_code == 200
    assert admin.post(f"{BASE}admin/{sid}/publish/").status_code == 200

    world["learner"].put(f"{BASE}{sid}/interaction/", {"status": "Trying"}, format="json")
    stats = admin.get(f"{BASE}admin/{sid}/interactions/").json()["response"]
    assert stats["counts"] == {"Trying": 1}
    uid = world["learner_user"].id
    assert admin.delete(f"{BASE}admin/{sid}/interactions/{uid}/").status_code == 200

    assert admin.post(f"{BASE}admin/{sid}/unpublish/").status_code == 200
    assert admin.delete(f"{BASE}admin/{sid}/").status_code == 200
    assert not ProblemStatement.objects.filter(id=sid).exists()


def test_admin_creates_for_any_company(world):
    res = world["admin"].post(
        BASE + "admin/", {**PAYLOAD, "company_id": world["company_b"].id}, format="json"
    )
    assert res.status_code == 200 and res.json()["response"]["company"]["id"] == str(world["company_b"].id)
    missing = world["admin"].post(BASE + "admin/", PAYLOAD, format="json")
    assert missing.status_code == 400
