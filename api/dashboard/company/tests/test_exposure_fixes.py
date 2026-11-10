"""Release 1.91 exposure fixes (BE-4, BE-6, BE-7, BE-8, BE-11). DB-free."""
from unittest import mock


def test_company_detail_exposes_publish_impact_report():
    from api.dashboard.company.serializers import CompanyDetailSerializer

    assert "publish_impact_report" in CompanyDetailSerializer().fields
