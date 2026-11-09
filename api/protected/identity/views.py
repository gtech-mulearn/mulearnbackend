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
import logging

from decouple import config
from django.db import IntegrityError, transaction
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from api.email_verification import service, tokens
from api.email_verification.errors import VerificationError, error_response
from api.email_verification.service import mark_email_verified_if_current
from api.register.serializers import UserDetailSerializer, UserSerializer
from db.user import User
from mu_celery.task import send_email
from utils.response import CustomResponse

logger = logging.getLogger(__name__)


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


# Providers whose verified address replaces the code (spec C D2a). authserver
# sends one only after verifying the provider's ID token says it is verified.
_PROVIDER_PROOFS = frozenset({"google", "apple"})


class _ProofNotRecorded(Exception):
    """The member was created but its proof could not be recorded."""


def _proven_via(email, token, via):
    """What this signup proved: "signup", "google", "apple", or None (spec C §4.4)."""
    if token and tokens.signup_token_matches(token, email):
        return "signup"
    if via in _PROVIDER_PROOFS:
        return via
    return None


def _protected(request, action, *args):
    """Run a spec A action for authserver: key first, spec A's envelope for refusals."""
    if not _key_is_valid(request.headers.get("protectionKey")):
        return CustomResponse(general_message="Invalid Key").get_failure_response()
    try:
        return CustomResponse(response=action(*args)).get_success_response()
    except VerificationError as error:
        return error_response(error.code, **error.extra)


class SignupCodeAPI(APIView):
    """
    Mail an express-signup code (spec C §4.4).

    Every call comes from authserver's address, so there is deliberately no
    throttle_scope here: authserver limits per client IP, and spec A's
    per-email limits apply inside codes.py whoever calls.
    """

    @extend_schema(
        tags=["Protected - Identity"],
        description="Send an express-signup code. Internal use only.",
    )
    def post(self, request):
        return _protected(request, service.send_signup_code, request.data.get("email"))


class SignupCodeVerifyAPI(APIView):
    """Check an express-signup code and return spec A's signed signup token."""

    @extend_schema(
        tags=["Protected - Identity"],
        description="Check an express-signup code. Internal use only.",
    )
    def post(self, request):
        return _protected(
            request, service.verify_signup_code, request.data.get("email"), request.data.get("code")
        )


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
        description="Create a member from name and email, without a password. Internal use only.",
    )
    def post(self, request):
        if not _key_is_valid(request.headers.get("protectionKey")):
            # Deliberately terse: this endpoint should be unreachable from
            # outside, so a caller getting it wrong learns nothing useful.
            return CustomResponse(general_message="Invalid Key").get_failure_response()

        email = (request.data.get("email") or "").strip().lower()
        full_name = (request.data.get("full_name") or "").strip()
        # Any `password` in the body is deliberately ignored (Q22): the member
        # is created without one and authserver, the only writer of
        # user.password, sets it straight afterwards.

        if not email or not full_name:
            return CustomResponse(
                general_message="full_name and email are required"
            ).get_failure_response()

        # Spec C D2: no account exists without a proven inbox, whoever calls.
        via = _proven_via(
            email,
            request.data.get("email_verification_token"),
            request.data.get("email_verified_via"),
        )
        if via is None:
            return error_response("email_verification_required", email_verification_required=True)

        # Report an existing account as a distinct, non-fatal outcome. The
        # caller needs to tell the person "you already have an account, sign in"
        # rather than showing them a validation error on a signup form.
        # User.every, not User.objects: suspended members are hidden from
        # User.objects but still hold their email under the unique constraint.
        if User.every.filter(email=email).exists():
            return CustomResponse(
                general_message="An account already exists for this email",
                response={"already_exists": True},
            ).get_failure_response()

        # The existing registration serializer, unchanged. It issues the muid
        # and creates the wallet, level, socials, settings and role link. Using
        # it directly is the point of this endpoint.
        serializer = UserSerializer(data={"full_name": full_name, "email": email})
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Could not create the account",
                response={"errors": serializer.errors},
            ).get_failure_response()

        # The serializer writes the user and then its wallet, socials, settings,
        # level and role link. Legacy registration runs that inside
        # RegisterSerializer's transaction; this call must too, or a failure
        # midway leaves a half-provisioned member whose email blocks a retry.
        try:
            with transaction.atomic():
                user = serializer.save()
                # Same transaction, so the member never exists unverified.
                if not mark_email_verified_if_current(user.id, email, via):
                    raise _ProofNotRecorded()
        except _ProofNotRecorded:
            logger.error("Provisioning could not record the %s proof; the new member was rolled back", via)
            return CustomResponse(general_message="Could not create the account").get_failure_response()
        except IntegrityError:
            # A concurrent signup for the same email won the race past the
            # exists() check above. Our writes are rolled back; report it the
            # same way.
            if User.every.filter(email=email).exists():
                return CustomResponse(
                    general_message="An account already exists for this email",
                    response={"already_exists": True},
                ).get_failure_response()
            raise

        # Same welcome email as the legacy dashboard signup, so members joining
        # through "Sign in with muLearn" are not treated differently. A mail or
        # queue failure must not undo a created account, so it is only logged.
        try:
            send_email.delay(
                UserDetailSerializer(user, many=False).data,
                "YOUR TICKET TO µFAM IS HERE!",
                ["user_registration.html"],
            )
        except Exception:
            logger.exception("Could not queue the welcome email for %s", user.id)

        return CustomResponse(
            response={"user_id": user.id, "muid": user.muid, "email": user.email}
        ).get_success_response()
