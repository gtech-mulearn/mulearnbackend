"""
Email verification orchestration (spec A §3.3-§3.6).

Views stay thin: every rule (validation, limits, what counts as proof) lives
here or in codes/tokens, and every failure is a VerificationError code.
"""
import logging

from django.contrib.auth.hashers import check_password
from django.db import IntegrityError, transaction
from django.utils import timezone

from db.user import User
from utils.emails import is_valid_email, mask_email, normalize_email
from utils.utils import send_template_mail

from . import codes, tokens
from .errors import VerificationError

logger = logging.getLogger(__name__)


def is_email_verified(user):
    """True iff the user's CURRENT email is proven (User.save() keeps this honest)."""
    return user.email_verified_at is not None


def mark_email_verified_if_current(user_id, email, via):
    """
    Fill a NULL verification for `email`, only while it is still the user's
    email (§3.6). The comparison happens here, not in SQL: the column's
    collation folds accents as well as case, so SQL would credit proof of one
    address to a look-alike.
    """
    proven = normalize_email(email)
    if not proven:
        return False
    with transaction.atomic():
        row = (
            User.every.select_for_update()
            .filter(id=user_id)
            .values("email", "email_verified_at")
            .first()
        )
        if not row or row["email_verified_at"] is not None:
            return False
        if normalize_email(row["email"]) != proven:
            return False
        User.every.filter(id=user_id, email_verified_at__isnull=True).update(
            email_verified_at=timezone.now().replace(microsecond=0),
            email_verified_via=via,
        )
    return True


def resolve_signup_verification(*, email, token, is_google_signup, google_email_verified):
    """
    What a new signup has proven (§3.3): the `via` to record once the user
    exists. Raises when nothing is proven: verification is unconditional
    (spec C D2), and an unverified provider address proves nothing (D2a).
    """
    if is_google_signup:
        if google_email_verified:
            return "google"
        raise VerificationError("email_verification_required")
    if tokens.signup_token_matches(token, email):
        return "signup"
    raise VerificationError("email_verification_required")


def status(user):
    return {
        "email": user.email,
        "verified": is_email_verified(user),
        "verified_at": user.email_verified_at,
        "via": user.email_verified_via,
        "has_password": bool(user.password),
    }


def send_signup_code(email):
    email = normalize_email(email)
    if not is_valid_email(email):
        raise VerificationError("invalid_email")
    if _email_in_use(email):
        raise VerificationError("email_taken")
    return _deliver("signup", email, email)


def verify_signup_code(email, code):
    email = normalize_email(email)
    codes.verify_code("signup", email, code)
    return {
        "email_verification_token": tokens.make_signup_token(email),
        "expires_in": tokens.SIGNUP_TOKEN_MAX_AGE,
    }


def request_account_code(user):
    if is_email_verified(user):
        return {"already_verified": True}
    return _deliver("account", user.id, normalize_email(user.email))


def confirm_account_code(user, code):
    email = codes.verify_code("account", user.id, code)
    if not mark_email_verified_if_current(user.id, email, "account") and _verified_at(user.id) is None:
        # The email changed after the code was sent, so the code proves nothing now.
        raise VerificationError("code_expired")
    return {"verified": True, "verified_at": _verified_at(user.id)}


def request_email_change(user, new_email, current_password=None):
    new_email = normalize_email(new_email)
    if not is_valid_email(new_email):
        raise VerificationError("invalid_email")
    if new_email == normalize_email(user.email):
        raise VerificationError("email_unchanged")
    if user.password:
        # A hijacked session must not be able to move the account (§3.5).
        if not current_password:
            raise VerificationError("password_required")
        if not check_password(current_password, user.password):
            raise VerificationError("invalid_password")
    if _email_in_use(new_email, exclude_user_id=user.id):
        raise VerificationError("email_taken")
    return _deliver("change", user.id, new_email)


def confirm_email_change(user, code):
    new_email = codes.verify_code("change", user.id, code)
    _apply_email_change(user.id, new_email)
    logger.info("email_verification email_changed user=%s", user.id)
    return {"email": new_email, "verified": True}


def _email_in_use(email, exclude_user_id=None):
    # User.every, not objects: suspended users still hold their address.
    users = User.every.filter(email__iexact=email)
    if exclude_user_id:
        users = users.exclude(id=exclude_user_id)
    return users.exists()


def _verified_at(user_id):
    return User.every.filter(id=user_id).values_list("email_verified_at", flat=True).first()


def _apply_email_change(user_id, new_email):
    with transaction.atomic():
        if _email_in_use(new_email, exclude_user_id=user_id):
            raise VerificationError("email_taken")
        user = User.every.select_for_update().get(id=user_id)
        user.email = new_email
        user.mark_email_verified_on_save("email_change")
        try:
            user.save()
        except IntegrityError:
            # Someone registered the address between the check and the write.
            raise VerificationError("email_taken")


def _send_code_mail(purpose, email, code):
    send_template_mail(
        context={"email": email, "code": code, "purpose": purpose, "minutes": codes.CODE_TTL_SECONDS // 60},
        subject="Your µLearn verification code",
        address=["email_verification", "code.html"],
    )


def _deliver(purpose, subject, email):
    try:
        sent = codes.send_code(purpose, subject, email, lambda code: _send_code_mail(purpose, email, code))
    except codes.MailDeliveryFailed:
        logger.exception("email_verification send_failed purpose=%s to=%s", purpose, mask_email(email))
        raise VerificationError("mail_send_failed")
    logger.info("email_verification code_sent purpose=%s to=%s", purpose, mask_email(email))
    return {"expires_in": sent.expires_in, "resend_after": sent.resend_after, "sent_to": mask_email(email)}
