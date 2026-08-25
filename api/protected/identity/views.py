"""
Member provisioning for the identity provider.

Why this endpoint exists
------------------------
"Sign in with muLearn" puts signup on auth.mulearn.org, so a person never
leaves the identity host mid-flow. But creating a muLearn member means issuing
a muid and creating a wallet, a level, socials, settings and a role link - and
all of that logic lives here, in this repo's registration serializer.

Copying it into authserver would give two implementations of membership
creation that drift apart. That is exactly the failure mode audit finding F19
documented, where a manual mirroring step silently stopped being performed. So
authserver calls this instead, and this remains the only place a member is
created.

This is an INTERNAL endpoint. It is not part of the public API and no browser
should ever reach it.
"""

import hmac

from decouple import config
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from api.register.serializers import UserSerializer
from db.user import User
from utils.response import CustomResponse


def _key_is_valid(provided):
    """
    Constant-time comparison.

    The neighbouring protected views use `not provided == expected`, which
    short-circuits on the first differing byte. Timing recovery over HTTP is
    impractical, but this key authorises member creation, and the correct
    primitive costs nothing.
    """
    expected = config("PROTECTED_API_KEY")
    if not provided or not expected:
        return False
    return hmac.compare_digest(str(provided), str(expected))


class ProvisionMemberAPI(APIView):
    """
    Create a muLearn member from the minimum a signup form can collect.

    Everything not supplied - district, interests, date of birth - is simply
    absent. The member is complete and usable: they have a muid, a wallet and a
    level. They have not finished onboarding, which is a different thing and is
    reported separately.
    """

    @extend_schema(
        tags=["Protected - Identity"],
        description="Create a member from name, email and password. Internal use only.",
    )
    def post(self, request):
        if not _key_is_valid(request.headers.get("protectionKey")):
            # Deliberately terse: this endpoint should be unreachable from
            # outside, so a caller getting it wrong learns nothing useful.
            return CustomResponse(general_message="Invalid Key").get_failure_response()

        email = (request.data.get("email") or "").strip().lower()
        full_name = (request.data.get("full_name") or "").strip()
        password = request.data.get("password")

        if not email or not full_name:
            return CustomResponse(
                general_message="full_name and email are required"
            ).get_failure_response()

        # Report an existing account as a distinct, non-fatal outcome. The
        # caller needs to tell the person "you already have an account, sign in"
        # rather than showing them a validation error on a signup form.
        if User.objects.filter(email=email).exists():
            return CustomResponse(
                general_message="An account already exists for this email",
                response={"already_exists": True},
            ).get_failure_response()

        # The existing registration serializer, unchanged. It issues the muid
        # and creates the wallet, level, socials, settings and role link. Using
        # it directly is the point of this endpoint.
        serializer = UserSerializer(
            data={"full_name": full_name, "email": email, "password": password}
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Could not create the account",
                response={"errors": serializer.errors},
            ).get_failure_response()

        user = serializer.save()

        return CustomResponse(
            response={"user_id": user.id, "muid": user.muid, "email": user.email}
        ).get_success_response()
