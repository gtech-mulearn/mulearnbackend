"""
Firebase Cloud Messaging, behind one small interface so the rest of the push
code (and its tests) never touches firebase_admin directly.

FIREBASE_CREDENTIALS is a path to the service-account JSON or the JSON text
itself. Empty means push is not configured: is_configured() is False and the
sender logs `skipped_disabled` instead of failing.
"""
import json
import logging
import os
import threading
from dataclasses import dataclass
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# FCM accepts at most 500 tokens per multicast call.
MAX_TOKENS_PER_CALL = 500

# Error codes after which a token will never work again.
DEAD_TOKEN_CODES = {"UNREGISTERED", "NOT_FOUND", "INVALID_ARGUMENT", "SENDER_ID_MISMATCH"}

_app = None
_lock = threading.Lock()


@dataclass
class TokenResult:
    token: str
    ok: bool
    error_code: Optional[str] = None

    @property
    def dead(self) -> bool:
        return not self.ok and (self.error_code or "").upper() in DEAD_TOKEN_CODES


def _credentials_source() -> str:
    return (getattr(settings, "FIREBASE_CREDENTIALS", "") or "").strip()


def is_configured() -> bool:
    return bool(getattr(settings, "PUSH_ENABLED", True)) and bool(_credentials_source())


def _get_app():
    global _app
    if _app is not None:
        return _app
    with _lock:
        if _app is not None:
            return _app
        import firebase_admin
        from firebase_admin import credentials

        source = _credentials_source()
        if source.startswith("{"):
            cred = credentials.Certificate(json.loads(source))
        elif os.path.exists(source):
            cred = credentials.Certificate(source)
        else:
            raise RuntimeError("FIREBASE_CREDENTIALS is neither JSON nor a readable file")
        _app = firebase_admin.initialize_app(cred, name="mulearn-push")
        return _app


def _error_code(exc) -> Optional[str]:
    if exc is None:
        return None
    code = getattr(exc, "code", None)
    cause_name = type(exc).__name__
    # firebase_admin.messaging.UnregisteredError → code "NOT_FOUND"; keep the
    # class name too so the dead-token check catches either form.
    if cause_name == "UnregisteredError":
        return "UNREGISTERED"
    if cause_name == "SenderIdMismatchError":
        return "SENDER_ID_MISMATCH"
    return str(code).upper() if code else cause_name.upper()


def send_multicast(tokens: list, title: str, body: str, data: dict) -> list:
    """Send one message to up to MAX_TOKENS_PER_CALL tokens.
    Returns one TokenResult per token, in order. Never raises for per-token
    failures; raises only if the whole call fails (network, auth), so the
    Celery task can retry it."""
    if not tokens:
        return []
    if len(tokens) > MAX_TOKENS_PER_CALL:
        raise ValueError(f"at most {MAX_TOKENS_PER_CALL} tokens per call")
    from firebase_admin import messaging

    message = messaging.MulticastMessage(
        tokens=list(tokens),
        notification=messaging.Notification(title=title, body=body),
        # FCM data values must be strings.
        data={k: str(v) for k, v in (data or {}).items() if v is not None},
        android=messaging.AndroidConfig(
            priority="high",
            notification=messaging.AndroidNotification(
                channel_id="mulearn_default",
                click_action="FLUTTER_NOTIFICATION_CLICK",
            ),
        ),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(aps=messaging.Aps(sound="default")),
        ),
    )
    batch = messaging.send_each_for_multicast(message, app=_get_app())
    results = []
    for token, resp in zip(tokens, batch.responses):
        results.append(TokenResult(token, resp.success, _error_code(resp.exception)))
    return results
