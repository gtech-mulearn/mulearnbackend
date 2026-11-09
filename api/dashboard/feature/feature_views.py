from rest_framework.views import APIView

from utils.permission import CustomizePermission, verified_role_required
from utils.response import CustomResponse
from utils.types import RoleType

from .flags import FLAGS, is_flag_on, set_flag


class FeatureFlagAPI(APIView):
    """
    /api/v1/dashboard/feature/<slug>/ for every flag in flags.FLAGS.

    GET (any signed-in user) → {enabled}, plus {configured} for flags that need
    server settings. POST {enabled: bool} switches it (Admins only).
    """

    authentication_classes = [CustomizePermission]

    def get(self, request, slug):
        flag = FLAGS.get(slug)
        if flag is None:
            return _unknown()
        body = {"enabled": is_flag_on(flag.key, flag.default)}
        if flag.is_configured is not None:
            body["configured"] = flag.is_configured()
        return CustomResponse(response=body).get_success_response()

    # The token's role alone is not proof (signup accepts any role): the
    # guard also checks the database for a verified, live Admins link.
    @verified_role_required([RoleType.ADMIN.value])
    def post(self, request, slug):
        flag = FLAGS.get(slug)
        if flag is None:
            return _unknown()
        enabled = request.data.get("enabled")
        if not isinstance(enabled, bool):
            return CustomResponse(
                general_message="Invalid request body. 'enabled' (boolean) is required."
            ).get_failure_response()
        # Switching off always works; switching on needs the settings in place.
        if enabled and flag.is_configured is not None and not flag.is_configured():
            return CustomResponse(general_message=flag.not_configured_message).get_failure_response()
        set_flag(flag.key, enabled)
        return CustomResponse(
            general_message=f"{flag.label} has been successfully {'enabled' if enabled else 'disabled'}.",
            response={"enabled": enabled},
        ).get_success_response()


def _unknown():
    return CustomResponse(general_message="Unknown feature.").get_failure_response(
        status_code=404, http_status_code=404
    )
