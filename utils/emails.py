"""Email helpers shared by the User model and email verification (spec A)."""
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

USER_EMAIL_MAX_LENGTH = 200  # user.email is VARCHAR(200)


def normalize_email(value):
    """Strip and lowercase. Two addresses that normalise equal are one inbox.
    Anything but a string (JSON can carry any type) normalises to ""."""
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def is_valid_email(value):
    email = normalize_email(value)
    if not email or len(email) > USER_EMAIL_MAX_LENGTH:
        return False
    try:
        validate_email(email)
    except ValidationError:
        return False
    return True


def mask_email(value):
    """a•••@gmail.com: enough to recognise, not enough to harvest."""
    local, sep, domain = normalize_email(value).partition("@")
    if not sep or not local:
        return "•••"
    return f"{local[0]}•••@{domain}"
