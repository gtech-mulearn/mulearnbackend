"""Release 1.91 exposure fixes (BE-4, BE-6, BE-7, BE-8, BE-11). DB-free."""
from unittest import mock


def test_company_detail_exposes_publish_impact_report():
    from api.dashboard.company.serializers import CompanyDetailSerializer

    assert "publish_impact_report" in CompanyDetailSerializer().fields


def test_mentor_detail_lists_newest_application_first():
    import datetime

    from api.dashboard.mentor import serializers as mentor_serializers

    older = mock.Mock(updated_at=datetime.datetime(2026, 1, 1))
    newer = mock.Mock(updated_at=datetime.datetime(2026, 6, 1))
    obj = mock.Mock()
    obj.user.mentor_applications.all.return_value = [older, newer]
    with mock.patch.object(
        mentor_serializers, "MentorApplicationProfileSerializer"
    ) as app_serializer:
        app_serializer.side_effect = lambda apps, many: mock.Mock(data=list(apps))
        data = mentor_serializers.MentorDetailSerializer().get_applications(obj)

    assert data == [newer, older]


def test_public_ig_detail_hides_member_emails():
    from api.dashboard.ig.dash_ig_serializer import InterestGroupSerializer

    data = {
        "leads": [{"muid": "a@mulearn", "email": "a@x.com"}],
        "mentors": [{"muid": "b@mulearn", "email": "b@x.com"}],
        "thinktank": [{"muid": "c@mulearn", "email": "c@x.com"}],
    }
    public = InterestGroupSerializer(context={"strip_emails": True})
    stripped = public.apply_privacy(data)
    for field in ("leads", "mentors", "thinktank"):
        assert "email" not in stripped[field][0]

    internal = InterestGroupSerializer()
    assert internal.apply_privacy(
        {"leads": [{"email": "a@x.com"}]}
    )["leads"][0]["email"] == "a@x.com"


def test_mentor_detail_puts_undated_applications_last():
    import datetime

    from api.dashboard.mentor import serializers as mentor_serializers

    undated = mock.Mock(updated_at=None)
    dated = mock.Mock(
        updated_at=datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc)
    )
    obj = mock.Mock()
    obj.user.mentor_applications.all.return_value = [undated, dated]
    with mock.patch.object(
        mentor_serializers, "MentorApplicationProfileSerializer"
    ) as app_serializer:
        app_serializer.side_effect = lambda apps, many: mock.Mock(data=list(apps))
        data = mentor_serializers.MentorDetailSerializer().get_applications(obj)

    assert data == [dated, undated]
