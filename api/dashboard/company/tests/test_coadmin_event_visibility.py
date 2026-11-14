"""BE-10: accepted co-admins see their company's events in manage/. DB-free."""
from unittest import mock


def test_co_admin_without_company_role_gets_the_company_event_filter():
    from api.dashboard.events import manage_views

    with mock.patch.object(
        manage_views, "_get_user_company_org_ids", return_value=["org1"]
    ) as org_ids:
        q = manage_views._company_events_filter("u1", ["Student"])

    org_ids.assert_called_once_with("u1", ["Student"])
    assert q is not None
    assert ("organiser_org_id__in", ["org1"]) in q.children


def test_no_company_means_no_extra_filter():
    from api.dashboard.events import manage_views

    with mock.patch.object(
        manage_views, "_get_user_company_org_ids", return_value=[]
    ):
        assert manage_views._company_events_filter("u1", ["Student"]) is None
