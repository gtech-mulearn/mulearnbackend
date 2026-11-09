"""Partner SSO error codes (spec B §4) and their HTTP shape."""
from utils.response import CustomResponse

# code: (HTTP status, default message). {partner} becomes the partner's name.
ERRORS = {
    "not_eligible": (403, "You can't connect this account to {partner}."),
    "email_unverified": (403, "Verify your email to continue."),
    "consent_required": (409, "Review and accept the terms to continue."),
    "consent_version_mismatch": (400, "The terms have changed. Review them again to continue."),
    "email_not_supported": (422, "{partner} can't use this email address. Change your µLearn email to connect."),
    "email_in_use_by_other_link": (409, "This email is already linked to another {partner} account on µLearn. Contact µLearn support."),
    "in_progress": (409, "Already connecting. Please wait a moment."),
    "rate_limited": (429, "Too many attempts. Please wait a few minutes."),
    "feature_disabled": (404, "This integration isn't available."),
    "partner_rejected_field": (422, "{partner} couldn't accept some of your details. Check your profile and try again."),
    "partner_account_blocked": (403, "{partner} has blocked this account. Contact {partner} support."),
    "partner_conflict": (409, "This email is already used on {partner}. Contact {partner} support if it's your account."),
    "partner_busy": (429, "{partner} is busy right now. Try again in a minute."),
    "partner_unavailable": (503, "{partner} is temporarily unavailable. Try again in a minute."),
}


class PartnerError(Exception):
    """A failure the user sees as `message.error_code`."""

    def __init__(self, code, *, message=None, http_status=None, partner_code=None,
                 retry_after=None, reason=None, retryable=False):
        if code not in ERRORS:
            raise ValueError(f"unknown partner error code {code!r}")
        super().__init__(code)
        self.code = code
        self.message = message  # verbatim (e.g. the partner's own words); never .format()ted
        self.http_status = http_status or ERRORS[code][0]
        self.partner_code = partner_code
        self.retry_after = retry_after
        self.reason = reason
        self.retryable = retryable

    def text(self, partner_name):
        if self.message is not None:
            return self.message
        return ERRORS[self.code][1].format(partner=partner_name)


def error_response(error, partner_name):
    extra = {key: value for key, value in (("retry_after", error.retry_after), ("reason", error.reason))
             if value is not None}
    return CustomResponse(
        general_message=error.text(partner_name),
        message={"error_code": error.code},
        response=extra,
    ).get_failure_response(status_code=error.http_status, http_status_code=error.http_status)
