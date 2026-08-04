from rest_framework.views import APIView
from db.settings import SystemSetting
from utils.permission import CustomizePermission, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import DateTimeUtils


class GritMeterToggleAPI(APIView):
    """
    API endpoint for viewing and toggling the Grit Meter feature flag status.
    Located at /api/v1/dashboard/feature/grit-meter/
    Only users with the ADMIN role can modify (enable/disable) the feature flag.
    """
    authentication_classes = [CustomizePermission]

    def get(self, request):
        setting = SystemSetting.objects.filter(key="grit_meter_enabled").first()
        is_enabled = setting.value.lower() == "true" if setting else True
        return CustomResponse(response={"enabled": is_enabled}).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        enabled = request.data.get("enabled")
        if enabled is None or not isinstance(enabled, bool):
            return CustomResponse(
                general_message="Invalid request body. 'enabled' (boolean) is required."
            ).get_failure_response()

        setting, created = SystemSetting.objects.get_or_create(
            key="grit_meter_enabled",
            defaults={
                "value": str(enabled).lower(),
                "created_at": DateTimeUtils.get_current_utc_time(),
                "updated_at": DateTimeUtils.get_current_utc_time(),
            },
        )
        if not created:
            setting.value = str(enabled).lower()
            setting.updated_at = DateTimeUtils.get_current_utc_time()
            setting.save()

        status_str = "enabled" if enabled else "disabled"
        return CustomResponse(
            general_message=f"Grit Meter system has been successfully {status_str}.",
            response={"enabled": enabled},
        ).get_success_response()
