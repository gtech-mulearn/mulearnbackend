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


def make_community(admin_user, title, org_type="Community"):
    """An organization row; org_type 'Community' is what the community list returns."""
    from db.organization import Country, District, Organization, State, Zone
    kw = {"updated_by": admin_user, "created_by": admin_user}
    tag = f"pstest-{title}"
    country = Country.objects.create(name=tag, **kw)
    state = State.objects.create(name=tag, country=country, **kw)
    zone = Zone.objects.create(name=tag, state=state, **kw)
    district = District.objects.create(name=tag, zone=zone, **kw)
    return Organization.objects.create(
        title=tag, code=tag[-12:], org_type=org_type, district=district, **kw
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
        "admin_user": admin,
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


def test_unauthenticated_list_is_public(world):
    draft = create(world["a"]).json()["response"]["id"]
    published = create_published(world)
    res = APIClient().get(BASE, {"sortBy": "-published_at"})
    assert res.status_code == 200
    data = res.json()["response"]["data"]
    assert [s["id"] for s in data] == [published]
    assert data[0]["my_interaction"] is None


def test_unauthenticated_detail_is_public_for_published_only(world):
    draft = create(world["a"]).json()["response"]["id"]
    published = create_published(world)
    anon = APIClient()
    res = anon.get(f"{BASE}{published}/")
    assert res.status_code == 200
    assert res.json()["response"]["my_interaction"] is None
    assert anon.get(f"{BASE}{draft}/").json()["statusCode"] == 404


def test_unauthenticated_rejected_on_interaction_routes(world):
    sid = create_published(world)
    anon = APIClient()
    assert anon.get(f"{BASE}{sid}/interaction/").status_code in (401, 403)
    assert anon.put(f"{BASE}{sid}/interaction/", {}, format="json").status_code in (401, 403)
    assert anon.put(f"{BASE}{sid}/submission/", {}, format="json").status_code in (401, 403)


def test_invalid_token_rejected_on_public_routes(world):
    sid = create_published(world)
    anon = APIClient()
    anon.credentials(HTTP_AUTHORIZATION="Bearer not-a-jwt")
    assert anon.get(BASE).status_code in (401, 403)
    assert anon.get(f"{BASE}{sid}/").status_code in (401, 403)


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
    assert world["learner"].get(f"{url}counts/").json()["response"] == {"Trying": 1, "Submitted": 0}

    detail = world["learner"].get(f"{BASE}{sid}/").json()["response"]
    assert detail["my_interaction"] == "Trying" and detail["interaction_counts"] == {"Trying": 1, "Submitted": 0}

    assert world["learner"].delete(url).status_code == 200
    assert world["learner"].get(f"{url}counts/").json()["response"] == {"Trying": 0, "Submitted": 0}
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
    assert res["counts"] == {"Trying": 1, "Submitted": 0} and res["data"][0]["user_id"] == world["learner_user"].id
    assert world["b"].get(f"{BASE}company/{sid}/interactions/").json()["statusCode"] == 404


def test_admin_has_full_control(world):
    sid = create(world["a"]).json()["response"]["id"]
    admin = world["admin"]

    assert len(admin.get(BASE + "admin/").json()["response"]["data"]) == 1
    assert admin.patch(f"{BASE}admin/{sid}/", {"title": "Admin edit"}, format="json").status_code == 200
    assert admin.post(f"{BASE}admin/{sid}/publish/").status_code == 200

    world["learner"].put(f"{BASE}{sid}/interaction/", {"status": "Trying"}, format="json")
    stats = admin.get(f"{BASE}admin/{sid}/interactions/").json()["response"]
    assert stats["counts"] == {"Trying": 1, "Submitted": 0}
    uid = world["learner_user"].id
    assert admin.delete(f"{BASE}admin/{sid}/interactions/{uid}/").status_code == 200

    assert admin.post(f"{BASE}admin/{sid}/unpublish/").status_code == 200
    assert admin.delete(f"{BASE}admin/{sid}/").status_code == 200
    assert not ProblemStatement.objects.filter(id=sid).exists()


def _notes(company, title_part=""):
    from db.notification import Notification
    return Notification.objects.filter(user_id=company.company_user_id, title__icontains=title_part)


def test_admin_creates_for_verified_company_and_notifies(world):
    res = world["admin"].post(BASE + "admin/", {**PAYLOAD, "company_id": world["company_b"].id}, format="json")
    assert res.status_code == 200
    body = res.json()["response"]
    assert body["status"] == "Draft" and body["company"]["id"] == str(world["company_b"].id)
    sid = body["id"]
    ps = ProblemStatement.objects.get(id=sid)
    assert ps.source == ProblemStatement.Source.COMPANY and str(ps.company_id) == str(world["company_b"].id)
    assert _notes(world["company_b"], "created for your company").count() == 1
    # the owning company can now see, edit and publish it; the other company cannot
    assert world["b"].patch(f"{BASE}company/{sid}/", {"title": "Company edit"}, format="json").status_code == 200
    assert world["b"].post(f"{BASE}company/{sid}/publish/").status_code == 200
    assert world["a"].get(f"{BASE}company/{sid}/").status_code == 404
    # company editing its own statement: no extra notification
    assert _notes(world["company_b"], "updated").count() == 0


def test_admin_company_id_must_be_verified(world):
    pending = make_company(make_user("pending_owner"), "Pending")
    pending.status = "pending"
    pending.save()
    for bad in ("does-not-exist", pending.id):
        res = world["admin"].post(BASE + "admin/", {**PAYLOAD, "company_id": bad}, format="json")
        assert res.status_code == 404
    assert not ProblemStatement.objects.filter(title=PAYLOAD["title"]).exists()


def test_company_route_rejects_company_id(world):
    res = world["a"].post(BASE + "company/", {**PAYLOAD, "company_id": world["company_b"].id}, format="json")
    assert res.status_code == 400
    assert not ProblemStatement.objects.filter(company=world["company_b"]).exists()


def test_admin_edit_notifies_company_and_relinks(world):
    admin = world["admin"]
    sid = admin.post(BASE + "admin/", {**PAYLOAD, "company_id": world["company_a"].id}, format="json").json()["response"]["id"]
    assert admin.patch(f"{BASE}admin/{sid}/", {"description": "An updated long description."}, format="json").status_code == 200
    assert _notes(world["company_a"], "was updated").count() == 1
    # re-link a -> b
    res = admin.patch(f"{BASE}admin/{sid}/", {"company_id": world["company_b"].id}, format="json")
    assert res.status_code == 200 and res.json()["response"]["company"]["id"] == str(world["company_b"].id)
    assert _notes(world["company_b"], "assigned").count() == 1
    assert _notes(world["company_a"], "moved from").count() == 1
    # clear -> muLearn statement
    res = admin.patch(f"{BASE}admin/{sid}/", {"company_id": None}, format="json")
    assert res.json()["response"]["company"]["name"] == "muLearn"
    assert ProblemStatement.objects.get(id=sid).source == ProblemStatement.Source.MULEARN
    assert _notes(world["company_b"], "moved from").count() == 1


def test_admin_patch_blank_company_id_keeps_link_and_same_id_is_noop(world):
    admin = world["admin"]
    sid = admin.post(BASE + "admin/", {**PAYLOAD, "company_id": world["company_a"].id}, format="json").json()["response"]["id"]
    res = admin.patch(f"{BASE}admin/{sid}/", {"company_id": "", "title": "Same company"}, format="json")
    assert res.status_code == 200 and res.json()["response"]["company"]["id"] == str(world["company_a"].id)
    before = _notes(world["company_a"], "assigned").count() + _notes(world["company_a"], "moved from").count()
    assert admin.patch(f"{BASE}admin/{sid}/", {"company_id": world["company_a"].id}, format="json").status_code == 200
    after = _notes(world["company_a"], "assigned").count() + _notes(world["company_a"], "moved from").count()
    assert before == after == 0
    # relinking to a company that is not verified is rejected under the lock, link unchanged
    world["company_b"].status = "pending"
    world["company_b"].save()
    assert admin.patch(f"{BASE}admin/{sid}/", {"company_id": world["company_b"].id}, format="json").status_code == 404
    assert str(ProblemStatement.objects.get(id=sid).company_id) == str(world["company_a"].id)


# ----------------------------------------------------------------- on behalf of a community

def _post_admin(world, **extra):
    return world["admin"].post(BASE + "admin/", {**PAYLOAD, **extra}, format="json")


def test_admin_creates_for_community(world):
    from db.notification import Notification
    community = make_community(world["admin_user"], "GTech")
    before = Notification.objects.count()
    res = _post_admin(world, community_id=community.id)
    assert res.status_code == 200
    body = res.json()["response"]
    assert body["status"] == "Draft" and body["source"] == "community"
    assert body["company"] == {"id": str(community.id), "name": community.title, "logo": None}
    ps = ProblemStatement.objects.get(id=body["id"])
    assert ps.source == ProblemStatement.Source.COMMUNITY and ps.company_id is None
    assert str(ps.community_id) == str(community.id)
    assert Notification.objects.count() == before  # communities are not notified


def test_community_id_must_be_a_community(world):
    college = make_community(world["admin_user"], "AColl", org_type="College")
    for bad in ("does-not-exist", college.id):
        assert _post_admin(world, community_id=bad).status_code == 404
    assert not ProblemStatement.objects.filter(title=PAYLOAD["title"]).exists()


def test_company_and_community_together_rejected(world):
    community = make_community(world["admin_user"], "Both")
    res = _post_admin(world, community_id=community.id, company_id=world["company_a"].id)
    assert res.status_code == 400
    assert not ProblemStatement.objects.filter(title=PAYLOAD["title"]).exists()


def test_company_route_rejects_community_id(world):
    community = make_community(world["admin_user"], "NoCo")
    res = world["a"].post(BASE + "company/", {**PAYLOAD, "community_id": community.id}, format="json")
    assert res.status_code == 400


def test_community_statement_hidden_from_companies_and_shown_to_learners(world):
    community = make_community(world["admin_user"], "Vis")
    sid = _post_admin(world, community_id=community.id).json()["response"]["id"]
    assert world["a"].get(BASE + "company/").json()["response"]["data"] == []
    assert world["a"].get(f"{BASE}company/{sid}/").status_code == 404
    assert world["admin"].post(f"{BASE}admin/{sid}/publish/").status_code == 200
    row = next(r for r in world["learner"].get(BASE).json()["response"]["data"] if r["id"] == sid)
    assert row["company"]["name"] == community.title and row["source"] == "community"
    only = world["learner"].get(BASE, {"community_id": community.id}).json()["response"]["data"]
    assert [r["id"] for r in only] == [sid]
    assert world["learner"].get(BASE, {"source": "community"}).json()["response"]["data"]


def test_admin_relinks_between_company_community_and_mulearn(world):
    from db.notification import Notification
    admin = world["admin"]
    community = make_community(world["admin_user"], "Move")
    other = make_community(world["admin_user"], "Move2")
    sid = _post_admin(world, community_id=community.id).json()["response"]["id"]
    url = f"{BASE}admin/{sid}/"

    # blank is ignored, same id is a no-op, plain edit keeps the link
    res = admin.patch(url, {"community_id": "", "title": "Still community"}, format="json")
    assert res.json()["response"]["source"] == "community"
    assert admin.patch(url, {"community_id": community.id}, format="json").status_code == 200

    res = admin.patch(url, {"community_id": other.id}, format="json")
    assert res.json()["response"]["company"]["id"] == str(other.id)

    # community -> company: the community link is cleared, the company is told
    res = admin.patch(url, {"company_id": world["company_a"].id}, format="json")
    body = res.json()["response"]
    assert body["source"] == "company" and body["company"]["id"] == str(world["company_a"].id)
    ps = ProblemStatement.objects.get(id=sid)
    assert ps.community_id is None
    assert Notification.objects.filter(user_id=world["company_a"].company_user_id, title__icontains="assigned").count() == 1

    # company -> community: the company link is cleared, the old company is told
    res = admin.patch(url, {"community_id": community.id}, format="json")
    assert res.json()["response"]["source"] == "community"
    ps = ProblemStatement.objects.get(id=sid)
    assert ps.company_id is None and str(ps.community_id) == str(community.id)
    assert Notification.objects.filter(user_id=world["company_a"].company_user_id, title__icontains="moved from").count() == 1

    # explicit null unlinks -> muLearn
    res = admin.patch(url, {"community_id": None}, format="json")
    assert res.json()["response"]["company"]["name"] == "muLearn"
    assert ProblemStatement.objects.get(id=sid).source == ProblemStatement.Source.MULEARN


def test_admin_relink_to_non_community_rejected_and_link_kept(world):
    community = make_community(world["admin_user"], "Keep")
    college = make_community(world["admin_user"], "KeepColl", org_type="College")
    sid = _post_admin(world, community_id=community.id).json()["response"]["id"]
    res = world["admin"].patch(f"{BASE}admin/{sid}/", {"community_id": college.id}, format="json")
    assert res.status_code == 404
    assert str(ProblemStatement.objects.get(id=sid).community_id) == str(community.id)


def test_company_notification_failure_does_not_fail_create(world, monkeypatch):
    from api.notification.notifications_utils import NotificationUtils

    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(NotificationUtils, "insert_notification", boom)
    res = world["admin"].post(BASE + "admin/", {**PAYLOAD, "company_id": world["company_a"].id}, format="json")
    assert res.status_code == 200


def test_admin_create_is_mulearn_sourced(world):
    res = world["admin"].post(BASE + "admin/", PAYLOAD, format="json")
    assert res.status_code == 200
    body = res.json()["response"]
    assert body["company"] == {"id": None, "name": "muLearn", "logo": None}

    sid = body["id"]
    ps = ProblemStatement.objects.get(id=sid)
    assert ps.source == ProblemStatement.Source.MULEARN
    assert ps.company_id is None

    world["admin"].post(f"{BASE}admin/{sid}/publish/")

    admin_row = next(r for r in world["admin"].get(BASE + "admin/").json()["response"]["data"] if r["id"] == sid)
    assert admin_row["company"] == {"id": None, "name": "muLearn", "logo": None}

    learner_row = next(r for r in world["learner"].get(BASE).json()["response"]["data"] if r["id"] == sid)
    assert learner_row["company"] == {"id": None, "name": "muLearn", "logo": None}


# ----------------------------------------------------------------- P1 regressions

def test_edit_after_publish_does_not_undo_publication(world):
    """A PATCH only writes the columns it changes, so it can't restore stale status/published_*."""
    from utils import problem_statement as ps_utils

    sid = create(world["a"]).json()["response"]["id"]
    stale = ProblemStatement.objects.get(id=sid)  # read while still a draft
    assert stale.status == "Draft"
    world["a"].post(f"{BASE}company/{sid}/publish/")

    assert ps_utils.apply_changes(sid, {"title": "Edited while publishing"}, world["company_a"].company_user_id) is None
    ps = ProblemStatement.objects.get(id=sid)
    assert ps.title == "Edited while publishing"
    assert ps.status == "Published" and ps.published_at is not None and ps.published_by_id


def test_publish_does_not_overwrite_concurrent_edit(world):
    from utils import problem_statement as ps_utils

    sid = create(world["a"]).json()["response"]["id"]
    ps_utils.apply_changes(sid, {"title": "Edited before publish"}, world["company_a"].company_user_id)
    assert world["a"].post(f"{BASE}company/{sid}/publish/").status_code == 200
    assert ProblemStatement.objects.get(id=sid).title == "Edited before publish"


def test_deleting_an_actor_keeps_the_statement_and_interactions(world):
    sid = create_published(world)
    world["learner"].put(f"{BASE}{sid}/interaction/", {"status": "Trying"}, format="json")
    admin_user = User.objects.get(id="pstest_admin")
    world["admin"].patch(f"{BASE}admin/{sid}/", {"title": "Edited by admin"}, format="json")
    assert ProblemStatement.objects.get(id=sid).updated_by_id == admin_user.id

    admin_user.delete()

    ps = ProblemStatement.objects.get(id=sid)  # still there
    assert ps.updated_by_id == str(settings.SYSTEM_ADMIN_ID)
    assert ProblemStatementInteraction.objects.filter(problem_statement_id=sid).count() == 1


# ----------------------------------------------------------------- review regressions

def test_skill_filter_matches_decoded_values_ignoring_case(world):
    sid = create(world["a"], skills=["Python\ML", 'Say "Hi"', "C++", "Ünï"]).json()["response"]["id"]
    world["a"].post(f"{BASE}company/{sid}/publish/")
    for skill in ["python\ml", 'say "hi"', "c++", "ÜNÏ"]:
        res = world["learner"].get(BASE, {"skill": skill}).json()["response"]
        assert [s["id"] for s in res["data"]] == [sid], skill
    for skill in ["python", "ML", "%", "_", '"']:  # whole values only, no substring / wildcard hits
        assert world["learner"].get(BASE, {"skill": skill}).json()["response"]["data"] == [], skill


def test_interaction_on_statement_deleted_mid_request_is_not_found(world, monkeypatch):
    from api.dashboard.problem_statement import learner_views

    sid = create_published(world)
    stale = ProblemStatement.objects.get(id=sid)
    ProblemStatement.objects.filter(id=sid).delete()
    # the view looked the statement up just before it was deleted
    monkeypatch.setattr(learner_views, "_published_or_none", lambda _id: stale)
    res = world["learner"].put(f"{BASE}{sid}/interaction/", {"status": "Trying"}, format="json")
    assert res.status_code == 404
    assert res.json()["message"]["general"] == ["Problem statement not found."]


# ----------------------------------------------------------------- submissions

LINK = "https://github.com/pstest/solution#readme"


def submit(world, sid, url=LINK, client_key="learner"):
    return world[client_key].put(f"{BASE}{sid}/submission/", {"submission_url": url}, format="json")


def expire(sid):
    ProblemStatement.objects.filter(id=sid).update(deadline=timezone.now() - timedelta(minutes=1))


def test_submit_sets_link_status_and_counts(world):
    sid = create_published(world)
    res = submit(world, sid)
    assert res.status_code == 200
    body = res.json()["response"]
    assert body["status"] == "Submitted" and body["submission_url"] == LINK
    assert body["submitted_at"] is not None
    assert body["counts"] == {"Trying": 0, "Submitted": 1}

    mine = world["learner"].get(f"{BASE}{sid}/interaction/").json()["response"]
    assert mine["status"] == "Submitted" and mine["submission_url"] == LINK
    assert world["learner"].get(f"{BASE}{sid}/").json()["response"]["my_interaction"] == "Submitted"


def test_resubmit_replaces_link_without_duplicate(world):
    sid = create_published(world)
    world["learner"].put(f"{BASE}{sid}/interaction/", {}, format="json")  # Trying first
    submit(world, sid)
    assert submit(world, sid, "https://gitlab.com/pstest/v2").status_code == 200
    rows = ProblemStatementInteraction.objects.filter(problem_statement_id=sid)
    assert rows.count() == 1 and rows.get().submission_url == "https://gitlab.com/pstest/v2"


@pytest.mark.parametrize("url", [
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "http://github.com/pstest/solution",   # https only
    "github.com/pstest/solution",          # no scheme
    "https://",                            # no host
    "https://user:pass@github.com/x",      # credentials
    "https://github.com@evil.com/x",
    "https://evil.com\\@github.com/x",    # backslash
    "https://github.com/a b",              # whitespace
    "https://127.0.0.1/x",                 # IP literal
    "https://2130706433/x",                # integer IP form
    "https://localhost/x",
    "https://github.com/" + "a" * 500,     # too long
])
def test_submit_rejects_unsafe_or_malformed_links(world, url):
    sid = create_published(world)
    assert submit(world, sid, url).status_code == 400
    assert not ProblemStatementInteraction.objects.filter(problem_statement_id=sid).exists()


def test_submit_blocked_on_unpublished_and_after_deadline(world):
    sid = create_published(world)
    world["a"].post(f"{BASE}company/{sid}/unpublish/")
    assert submit(world, sid).json()["statusCode"] == 404

    open_sid = create_published(world)
    expire(open_sid)
    assert submit(world, open_sid).json()["statusCode"] == 409


def test_withdraw_submission_reverts_to_trying(world):
    sid = create_published(world)
    submit(world, sid)
    assert world["learner"].delete(f"{BASE}{sid}/submission/").status_code == 200
    row = ProblemStatementInteraction.objects.get(problem_statement_id=sid)
    assert row.status == "Trying" and row.submission_url is None and row.submitted_at is None
    assert world["learner"].delete(f"{BASE}{sid}/submission/").json()["statusCode"] == 404


def test_submission_locked_after_deadline(world):
    sid = create_published(world)
    submit(world, sid)
    expire(sid)
    assert world["learner"].delete(f"{BASE}{sid}/submission/").json()["statusCode"] == 409
    assert world["learner"].delete(f"{BASE}{sid}/interaction/").json()["statusCode"] == 409
    row = ProblemStatementInteraction.objects.get(problem_statement_id=sid)
    assert row.status == "Submitted" and row.submission_url == LINK


def test_interaction_put_cannot_submit_or_downgrade(world):
    sid = create_published(world)
    url = f"{BASE}{sid}/interaction/"
    assert world["learner"].put(url, {"status": "Submitted"}, format="json").status_code == 400
    submit(world, sid)
    res = world["learner"].put(url, {"status": "Trying"}, format="json")
    assert res.status_code == 200 and res.json()["response"]["status"] == "Submitted"
    assert ProblemStatementInteraction.objects.get(problem_statement_id=sid).submission_url == LINK


def test_submission_ignores_body_user(world):
    sid = create_published(world)
    other = make_user("other_sub")
    res = world["learner"].put(
        f"{BASE}{sid}/submission/", {"submission_url": LINK, "user_id": other.id}, format="json"
    )
    assert res.status_code == 400
    assert not ProblemStatementInteraction.objects.filter(user_id=other.id).exists()


def test_company_sees_submissions_only_for_own_statement(world):
    sid = create_published(world)
    submit(world, sid)
    trier = client_for(make_user("trier"))
    trier.put(f"{BASE}{sid}/interaction/", {}, format="json")

    res = world["a"].get(f"{BASE}company/{sid}/interactions/", {"status": "Submitted"}).json()["response"]
    assert res["counts"] == {"Trying": 1, "Submitted": 1}
    assert [(r["user_id"], r["submission_url"]) for r in res["data"]] == [(world["learner_user"].id, LINK)]
    assert world["b"].get(f"{BASE}company/{sid}/interactions/").json()["statusCode"] == 404


def test_mulearn_statement_submission_visible_to_admin(world):
    sid = world["admin"].post(BASE + "admin/", PAYLOAD, format="json").json()["response"]["id"]
    world["admin"].post(f"{BASE}admin/{sid}/publish/")
    assert submit(world, sid).status_code == 200
    rows = world["admin"].get(f"{BASE}admin/{sid}/interactions/").json()["response"]["data"]
    assert rows[0]["submission_url"] == LINK


def test_source_filter(world):
    company_sid = create_published(world)
    mulearn_sid = world["admin"].post(BASE + "admin/", PAYLOAD, format="json").json()["response"]["id"]
    world["admin"].post(f"{BASE}admin/{mulearn_sid}/publish/")

    def ids(client, url, source):
        return {s["id"] for s in client.get(url, {"source": source}).json()["response"]["data"]}

    assert ids(world["learner"], BASE, "mulearn") == {mulearn_sid}
    assert ids(world["learner"], BASE, "company") == {company_sid}
    assert ids(world["learner"], BASE, "bogus") == {company_sid, mulearn_sid}  # unknown value ignored
    assert ids(world["admin"], BASE + "admin/", "mulearn") == {mulearn_sid}


def test_company_label_falls_back_when_company_missing(world):
    """A source/company mismatch made outside the API must not 500 the list."""
    from api.dashboard.problem_statement.serializers import ProblemStatementSerializer

    sid = create(world["a"]).json()["response"]["id"]
    ps = ProblemStatement.objects.select_related("company").get(id=sid)
    ps.company = None  # in memory only; source stays "company"
    assert ProblemStatementSerializer(ps).data["company"] == {"id": None, "name": "muLearn", "logo": None}


# ----------------------------------------------------------------- deadline race (check under lock)

def _stale_open_copy(monkeypatch, sid):
    """
    Simulate the race: the view's early, unlocked check sees the statement as it was
    (published, deadline open), while the row has changed by the time the write runs.
    """
    from api.dashboard.problem_statement import learner_views

    stale = ProblemStatement.objects.get(id=sid)
    monkeypatch.setattr(learner_views, "_published_or_none", lambda _id: stale)


def test_submit_rechecks_deadline_under_lock(world, monkeypatch):
    sid = create_published(world)
    _stale_open_copy(monkeypatch, sid)
    expire(sid)  # deadline passed while the request was waiting
    assert submit(world, sid).json()["statusCode"] == 409
    assert not ProblemStatementInteraction.objects.filter(problem_statement_id=sid).exists()


def test_resubmit_rechecks_deadline_under_lock(world, monkeypatch):
    sid = create_published(world)
    submit(world, sid)
    _stale_open_copy(monkeypatch, sid)
    expire(sid)
    assert submit(world, sid, "https://gitlab.com/pstest/too-late").json()["statusCode"] == 409
    row = ProblemStatementInteraction.objects.get(problem_statement_id=sid)
    assert row.submission_url == LINK  # the closed submission was not replaced


def test_submit_rechecks_published_under_lock(world, monkeypatch):
    sid = create_published(world)
    _stale_open_copy(monkeypatch, sid)
    world["a"].post(f"{BASE}company/{sid}/unpublish/")  # unpublished while the request was waiting
    assert submit(world, sid).json()["statusCode"] == 404
    assert not ProblemStatementInteraction.objects.filter(problem_statement_id=sid).exists()


def test_interaction_put_rechecks_deadline_under_lock(world, monkeypatch):
    sid = create_published(world)
    _stale_open_copy(monkeypatch, sid)
    expire(sid)
    assert world["learner"].put(f"{BASE}{sid}/interaction/", {}, format="json").json()["statusCode"] == 409
    assert not ProblemStatementInteraction.objects.filter(problem_statement_id=sid).exists()


def test_statement_delete_still_cascades(world):
    sid = create_published(world)
    submit(world, sid)
    assert world["a"].delete(f"{BASE}company/{sid}/").status_code == 200
    assert not ProblemStatement.objects.filter(id=sid).exists()
    assert not ProblemStatementInteraction.objects.filter(problem_statement_id=sid).exists()


# ----------------------------------------------------------------- on behalf of (muid)

def test_admin_creates_on_behalf_of_user_and_notifies(world):
    from db.notification import Notification
    target = make_user("mentioned")
    res = world["admin"].post(BASE + "admin/", {**PAYLOAD, "muid": target.muid}, format="json")
    assert res.status_code == 200
    body = res.json()["response"]
    assert body["on_behalf_of"] == {"id": target.id, "muid": target.muid, "full_name": target.full_name}
    assert Notification.objects.filter(user=target, title="Problem statement drafted for you").count() == 1


def test_admin_unknown_muid_rejected(world):
    res = world["admin"].post(BASE + "admin/", {**PAYLOAD, "muid": "nobody@mulearn"}, format="json")
    assert res.status_code == 400
    assert not ProblemStatement.objects.filter(title=PAYLOAD["title"]).exists()


def test_company_route_rejects_muid(world):
    target = make_user("mentioned2")
    res = world["a"].post(BASE + "company/", {**PAYLOAD, "muid": target.muid}, format="json")
    assert res.status_code == 400
    assert "Unknown field." in res.json()["message"]["muid"]


def test_admin_patch_change_and_clear_muid(world):
    from db.notification import Notification
    first, second = make_user("m1"), make_user("m2")
    admin = world["admin"]
    sid = admin.post(BASE + "admin/", {**PAYLOAD, "muid": first.muid}, format="json").json()["response"]["id"]
    # same user again: no second notification
    admin.patch(f"{BASE}admin/{sid}/", {"muid": first.muid}, format="json")
    assert Notification.objects.filter(user=first).count() == 1
    res = admin.patch(f"{BASE}admin/{sid}/", {"muid": second.muid}, format="json")
    assert res.json()["response"]["on_behalf_of"]["muid"] == second.muid
    assert Notification.objects.filter(user=second).count() == 1
    res = admin.patch(f"{BASE}admin/{sid}/", {"muid": ""}, format="json")
    assert res.json()["response"]["on_behalf_of"] is None


def test_learner_view_hides_on_behalf_of(world):
    target = make_user("m3")
    sid = world["admin"].post(BASE + "admin/", {**PAYLOAD, "muid": target.muid}, format="json").json()["response"]["id"]
    world["admin"].post(f"{BASE}admin/{sid}/publish/")
    assert "on_behalf_of" not in world["learner"].get(f"{BASE}{sid}/").json()["response"]
