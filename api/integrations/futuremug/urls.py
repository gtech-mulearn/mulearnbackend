from django.urls import re_path

from api.integrations.partner_sso import views

from .adapter import futuremug_adapter

ACCOUNT_TYPE = r"(?P<account_type>candidate|company|college)"

urlpatterns = [
    re_path(rf"^{ACCOUNT_TYPE}/$", views.PartnerConnectionAPI.as_view(adapter=futuremug_adapter)),
    re_path(rf"^{ACCOUNT_TYPE}/authorize/$", views.PartnerAuthorizeAPI.as_view(adapter=futuremug_adapter)),
    re_path(rf"^{ACCOUNT_TYPE}/sign-in/$", views.PartnerSignInAPI.as_view(adapter=futuremug_adapter)),
]
