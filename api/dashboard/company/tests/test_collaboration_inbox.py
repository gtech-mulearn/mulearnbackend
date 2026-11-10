"""BE-9: incoming collaboration invites for campus and IG leads. DB-free."""
from django.urls import resolve


def test_incoming_route_is_not_taken_as_a_collaboration_id():
    from api.dashboard.company import collaboration_views

    match = resolve("/api/v1/dashboard/company/collaborations/incoming/")
    assert match.func.view_class is collaboration_views.CompanyCollaborationIncomingAPI


def test_only_ig_lead_roles_count_as_ig_targets():
    from api.dashboard.company.collaboration_views import ig_codes_led

    roles = ["WEB IGLead", "AI IGLead", "WEB CampusIGLead", "Student", "IGLead"]
    assert ig_codes_led(roles) == ["WEB", "AI"]
