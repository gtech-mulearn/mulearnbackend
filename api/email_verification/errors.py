"""Error codes for email verification (spec A §4) and their HTTP shape."""
from utils.response import CustomResponse

MESSAGES = {
    "invalid_email": "Enter a valid email address.",
    "email_taken": "An account with this email already exists. Sign in instead.",
    "email_unchanged": "That's already your email address.",
    "code_cooldown": "Please wait before asking for another code.",
    "code_rate_limited": "Too many requests. Please try again later.",
    "invalid_code": "That code isn't right. Check the email and try again.",
    "code_expired": "This code has expired. Ask for a new one.",
    "mail_send_failed": "We couldn't send the email. Please try again.",
    "email_verification_required": "Please verify your email address to continue.",
    "email_change_requires_verification": "To change your email, use Account settings → Change email.",
    "password_required": "Enter your current password to change your email.",
    "invalid_password": "Your current password is incorrect.",
    "user_not_found": "We couldn't find your account.",
}

HTTP_STATUS = {
    "email_taken": 409,
    "code_cooldown": 429,
    "code_rate_limited": 429,
    "mail_send_failed": 503,
    "password_required": 403,
    "invalid_password": 403,
    "user_not_found": 404,
}


class VerificationError(Exception):
    def __init__(self, code, **extra):
        super().__init__(code)
        self.code = code
        self.extra = {key: value for key, value in extra.items() if value is not None}


def error_response(code, **extra):
    http_status = HTTP_STATUS.get(code, 400)
    return CustomResponse(
        general_message=MESSAGES[code],
        message={"error_code": code},
        response={key: value for key, value in extra.items() if value is not None},
    ).get_failure_response(status_code=http_status, http_status_code=http_status)
