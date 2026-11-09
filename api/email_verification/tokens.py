"""Signup tokens: proof that a code for this email was entered (spec A §3.3)."""
from django.core import signing

from utils.emails import normalize_email

SIGNUP_TOKEN_MAX_AGE = 3600
_SALT = "email-verification.signup"


def make_signup_token(email):
    return signing.dumps({"email": normalize_email(email)}, salt=_SALT)


def read_signup_token(token, max_age=SIGNUP_TOKEN_MAX_AGE):
    """The email inside a valid, unexpired token, else None."""
    if not isinstance(token, str):  # JSON bodies can carry any type
        return None
    try:
        data = signing.loads(token, salt=_SALT, max_age=max_age)
    except signing.BadSignature:  # includes SignatureExpired
        return None
    email = data.get("email") if isinstance(data, dict) else None
    return email or None


def signup_token_matches(token, email):
    if not token:
        return False
    found = read_signup_token(token)
    return found is not None and found == normalize_email(email)
