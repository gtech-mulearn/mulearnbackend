"""HTTP layer for partner SSO (spec B §4). Bound to an adapter in each provider's urls.py."""
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse

from . import service
from .errors import PartnerError, error_response

TAGS = ["Integrations - Partner SSO"]


class _PartnerView(APIView):
    permission_classes = [CustomizePermission]
    adapter = None  # bound per provider: View.as_view(adapter=…)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"  # login links are single-use secrets
        return response

    def run(self, http_request, action, account_type, **kwargs):
        # Not named `request`: actions take their own `request=` keyword.
        user = User.objects.filter(id=JWTUtils.fetch_user_id(http_request)).first()
        if user is None:  # suspended, or deleted since the token was issued
            return error_response(PartnerError("not_eligible", reason="suspended"), self.adapter.display_name)
        try:
            return CustomResponse(response=action(self.adapter, account_type, user, **kwargs)).get_success_response()
        except PartnerError as error:
            return error_response(error, self.adapter.display_name)


class PartnerConnectionAPI(_PartnerView):
    @extend_schema(tags=TAGS, description="Partner connection status for the current user's account-holder.")
    def get(self, request, account_type):
        return self.run(request, service.connection_status, account_type)

    @extend_schema(tags=TAGS, description="Disconnect: withdraw consent and stop sharing.")
    def delete(self, request, account_type):
        return self.run(request, service.disconnect, account_type, request=request)


class PartnerAuthorizeAPI(_PartnerView):
    @extend_schema(tags=TAGS, description="Record consent, then sign in to the partner.")
    def post(self, request, account_type):
        return self.run(request, service.authorize, account_type,
                        consent_version=request.data.get("consent_version"),
                        accepted=request.data.get("accepted"), request=request)


class PartnerSignInAPI(_PartnerView):
    @extend_schema(tags=TAGS, description="Sign in to the partner (reconciles contact details first).")
    def post(self, request, account_type):
        return self.run(request, service.sign_in, account_type)
