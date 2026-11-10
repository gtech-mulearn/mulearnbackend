"""BE-5: admin list of deactivated mentors, for reactivation. DB-free."""
from django.urls import resolve


def test_deactivated_route_resolves_to_the_list_view():
    from api.dashboard.mentor import admin_views

    match = resolve("/api/v1/dashboard/mentor/admin/deactivated/")
    assert match.func.view_class is admin_views.MentorDeactivatedListAPI


def test_rows_are_mentor_profiles_keyed_by_user_mentor_id():
    from api.dashboard.mentor.admin_views import MentorDeactivatedListAPI
    from api.dashboard.mentor.serializers import MentorDetailSerializer

    assert MentorDeactivatedListAPI.serializer_class is MentorDetailSerializer
    # MentorDetailSerializer models UserMentor, so "id" is what reactivate takes.
    assert MentorDetailSerializer.Meta.model.__name__ == "UserMentor"
    assert "id" in MentorDetailSerializer().fields
