"""JSON log lines that carry the request context and never carry personal data or secrets.

Selected with LOG_FORMAT=json. Any record attribute or extra key that names a sensitive value
(password, token, otp, email, phone, muid) is redacted, at any depth, as are variants such as
accessToken, refresh_token or user_email. The message text itself isn't parsed: log ids, never
personal data, in messages.
"""

import json
import logging
import re
from datetime import datetime, timezone

from building_blocks.observability import context

SENSITIVE = frozenset({"password", "token", "otp", "email", "phone", "muid"})
REDACTED = "[redacted]"

# Every attribute a plain LogRecord has; anything else on a record came from `extra`.
_STANDARD = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message", "asctime"}


def is_sensitive(key: str) -> bool:
    words = re.findall(r"[a-z0-9]+", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(key)).lower())
    return any(word in SENSITIVE for word in words)


def redact(value):
    if isinstance(value, dict):
        return {key: REDACTED if is_sensitive(key) else redact(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = redact(record.msg) if isinstance(record.msg, dict) and not record.args else record.getMessage()
        line = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds")[:-6] + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "request_id": context.current_request_id(),
            "user_id": context.current_user_id(),
            "trace_id": None,  # set once tracing lands (issue 0043)
        }
        for key, value in vars(record).items():
            if key not in _STANDARD and key not in line:
                line[key] = REDACTED if is_sensitive(key) else redact(value)
        if record.exc_info:
            line["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            line["stack"] = self.formatStack(record.stack_info)
        return json.dumps(line, default=str, ensure_ascii=False)
