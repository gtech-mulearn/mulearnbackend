"""
Feature flags behind System → Features, one row each in system_setting.

Read on hot paths (Futuremug's cards ask on every profile view), so a value is
cached for FLAG_CACHE_SECONDS in the shared Redis cache and written through on
change: every worker sees a switch at once, and the database is asked at most
once a minute per flag. A cache outage falls back to the database.
"""
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from django.core.cache import cache
from django.db import IntegrityError

from db.settings import SystemSetting
from utils.utils import DateTimeUtils

logger = logging.getLogger(__name__)

FLAG_CACHE_SECONDS = 60
_CACHE_KEY = "feature_flag:{}"


@dataclass(frozen=True)
class FeatureFlag:
    key: str  # the system_setting row
    default: bool  # when there is no row
    label: str  # in "<label> has been successfully enabled."
    # Flags that need server settings (keys, URLs) before they can work.
    is_configured: Optional[Callable[[], bool]] = None
    not_configured_message: str = ""


def is_flag_on(key: str, default: bool) -> bool:
    cache_key = _CACHE_KEY.format(key)
    try:
        cached = cache.get(cache_key)
    except Exception:
        logger.warning("feature flag cache read failed for %s; reading the database", key)
        cached = None
    if cached is not None:
        return cached
    row = SystemSetting.objects.filter(key=key).first()
    value = row.value.strip().lower() == "true" if row else default
    _remember(key, value)
    return value


def set_flag(key: str, enabled: bool) -> bool:
    value = str(enabled).lower()
    now = DateTimeUtils.get_current_utc_time()
    if not SystemSetting.objects.filter(key=key).update(value=value, updated_at=now):
        try:
            SystemSetting.objects.create(key=key, value=value, created_at=now, updated_at=now)
        except IntegrityError:  # another admin created it first
            SystemSetting.objects.filter(key=key).update(value=value, updated_at=now)
    _remember(key, enabled)
    return enabled


def _remember(key, value):
    try:
        cache.set(_CACHE_KEY.format(key), value, FLAG_CACHE_SECONDS)
    except Exception:
        logger.warning("feature flag cache write failed for %s", key)


def _futuremug_configured():
    from api.integrations.futuremug.adapter import futuremug_adapter  # the adapter reads these flags

    return futuremug_adapter.is_configured()


# URL slug → flag. Grit Meter's key, default and label predate this module.
FLAGS = {
    "grit-meter": FeatureFlag(key="grit_meter_enabled", default=True, label="Grit Meter system"),
    "futuremug": FeatureFlag(
        key="futuremug_enabled",
        default=False,
        label="Futuremug",
        is_configured=_futuremug_configured,
        not_configured_message="Futuremug isn't configured on this server: set its API key and URLs first.",
    ),
}
