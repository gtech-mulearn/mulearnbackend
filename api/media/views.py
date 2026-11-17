from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from db.task import InterestGroup
from utils.media_keys import validate_key
from utils.media_modules import MEDIA_MODULES
from utils.permission import BackendApiKeyPermission
from utils.response import CustomResponse

# Largest batch one request may ask about; the media worker sends fewer.
MAX_KEYS_PER_REQUEST = 500

# Every database column that can hold a media key: (model, field name).
# Add an entry here when a new module starts storing keys, or its images
# would look unused and be deleted by the media worker's cleanup.
MEDIA_KEY_COLUMNS = (
    (InterestGroup, "cover_image_key"),
    (InterestGroup, "icon_image_key"),
)


def referenced_keys(keys):
    """The subset of `keys` that some record still points at."""
    found = set()
    for model, field in MEDIA_KEY_COLUMNS:
        found.update(
            model.objects.filter(**{f"{field}__in": keys}).values_list(field, flat=True)
        )
    return found


class UnreferencedMediaKeysAPI(APIView):
    """
    Used by the media worker's scheduled cleanup (not by the frontend).

    The worker lists images in the bucket and asks which of them no record
    uses, then deletes those. This endpoint only answers the question; the
    backend holds no storage credentials and deletes nothing.
    """

    # Machine-to-machine: the shared Api-Key header, not a user login.
    authentication_classes = []
    permission_classes = [BackendApiKeyPermission]

    @extend_schema(
        tags=["Media"],
        description=(
            "Given storage keys, returns the ones that no record references. "
            "Requires the Api-Key header."
        ),
    )
    def post(self, request):
        keys = request.data.get("keys")
        if (
            not isinstance(keys, list)
            or not keys
            or len(keys) > MAX_KEYS_PER_REQUEST
            or not all(isinstance(k, str) for k in keys)
        ):
            return CustomResponse(
                general_message=f"'keys' must be a list of 1 to {MAX_KEYS_PER_REQUEST} strings"
            ).get_failure_response()

        # Only keys the media worker could have issued. Anything else is refused
        # so this cannot be used to probe other values.
        if not all(any(validate_key(module, k) for module in MEDIA_MODULES) for k in keys):
            return CustomResponse(
                general_message="'keys' contains a value that is not a media key"
            ).get_failure_response()

        unique = list(dict.fromkeys(keys))
        in_use = referenced_keys(unique)  # one query per column, not per key
        unreferenced = [k for k in unique if k not in in_use]
        return CustomResponse(response={"unreferenced": unreferenced}).get_success_response()
