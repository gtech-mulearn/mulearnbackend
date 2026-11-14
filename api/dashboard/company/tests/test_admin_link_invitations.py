"""Co-admin invitations for the invitee, and cancelling a pending invite (BE-1, BE-2).

DB-free: URL routing and serializer shape only.
"""
from django.urls import resolve


def test_invitations_route_is_not_swallowed_by_the_link_id_route():
    from api.dashboard.company import company_views

    match = resolve("/api/v1/dashboard/company/admin-link/invitations/")
    assert match.func.view_class is company_views.CompanyAdminLinkMyInvitationsAPI


def test_invitation_serializer_exposes_what_the_invitee_needs():
    from api.dashboard.company.serializers import CompanyAdminLinkInvitationSerializer

    assert list(CompanyAdminLinkInvitationSerializer().fields) == [
        "id",
        "company_id",
        "company_name",
        "company_logo",
        "invited_by_name",
        "invited_at",
    ]
