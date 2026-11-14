"""BE-3: admin queue of pending IG sponsorship requests. DB-free."""
import datetime
from unittest import mock

from django.urls import resolve


def test_pending_route_is_not_taken_as_an_ig_id():
    from api.dashboard.company import ig_sponsorship_views

    match = resolve("/api/v1/dashboard/company/ig-sponsorship/pending/")
    assert match.func.view_class is ig_sponsorship_views.IgSponsorshipPendingListAPI


def test_pending_rows_carry_what_the_admin_reviews():
    from api.dashboard.company.ig_sponsorship_views import pending_sponsorship_rows

    when = datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc)
    ig = mock.Mock(id="ig1", updated_at=when, sponsor_company_id="co1")
    ig.name = "Web Development"
    ig.sponsor_company.name = "Acme"

    assert pending_sponsorship_rows([ig]) == [
        {
            "ig_id": "ig1",
            "ig_name": "Web Development",
            "company_id": "co1",
            "company_name": "Acme",
            "requested_at": when,
        }
    ]
