"""Every setting mulearnbackend/settings.py reads, with its type (issue 0020, ADR-048).

A setting that was required before this declaration existed is required in every environment,
so startup behaves as it did. Narrow ``required_in`` to the environments that need a value,
for example ``frozenset({"staging", "production"})``, once that's been agreed. Check an env file
before a deploy with ``python manage.py config_check --env-file <path>``.
"""

from building_blocks.config import ALL_ENVIRONMENTS as ALL
from building_blocks.config import URL, Setting, declare

declare(
    Setting("MULEARN_ENV", str, default="local"),
    # Core
    Setting("SECRET_KEY", str, required_in=ALL, secret=True),
    Setting("DEBUG", bool, default=False),
    Setting("ALLOWED_HOSTS", list[str], required_in=ALL),
    Setting("SYSTEM_ADMIN_ID", str, required_in=ALL),
    Setting("DRAIN_FLAG_PATH", str, default="/tmp/mulearn-drain"),
    Setting("ENABLE_SWAGGER", bool, default=False),
    # Redis
    Setting("REDIS_HOST", str, required_in=ALL),
    Setting("REDIS_PORT", int, required_in=ALL),
    # Database. USER, PASSWORD, HOST and PORT are empty on the SQLite test tier.
    Setting("DATABASE_ENGINE", str, required_in=ALL),
    Setting("DATABASE_NAME", str, required_in=ALL),
    Setting("DATABASE_USER", str, required_in=ALL),
    Setting("DATABASE_PASSWORD", str, required_in=ALL, secret=True),
    Setting("DATABASE_HOST", str, required_in=ALL),
    Setting("DATABASE_PORT", str, required_in=ALL),
    # Logging
    Setting("LOGGER_DIR_PATH", str, required_in=ALL),
    Setting("LOG_LEVEL", str, default="WARNING"),
    Setting("LOG_FORMAT", str, default="text"),
    # Email
    Setting("EMAIL_BACKEND", str, required_in=ALL),
    Setting("EMAIL_HOST", str, required_in=ALL),
    Setting("EMAIL_HOST_USER", str, required_in=ALL),
    Setting("EMAIL_HOST_PASSWORD", str, required_in=ALL, secret=True),
    Setting("EMAIL_PORT", int, required_in=ALL),
    Setting("EMAIL_USE_TLS", bool, required_in=ALL),
    Setting("FROM_MAIL", str, required_in=ALL),
    Setting("FR_DOMAIN_NAME", str, required_in=ALL),
    # Integrations. An empty URL means the integration isn't configured.
    Setting("WADHWANI_CLIENT_AUTH_URL", URL, required_in=ALL),
    Setting("WADHWANI_CLIENT_SECRET", str, required_in=ALL, secret=True),
    Setting("WADHWANI_BASE_URL", URL, required_in=ALL),
    Setting("RAZORPAY_ID", str, required_in=ALL),
    Setting("RAZORPAY_SECRET", str, required_in=ALL, secret=True),
    Setting("QSEVERSE_BASE_URL", URL, required_in=ALL),
    Setting("QSEVERSE_API_KEY", str, required_in=ALL, secret=True),
    Setting("BACKEND_API_KEY", str, required_in=ALL, secret=True),
    Setting("R2_PUBLIC_BASE_URL", URL, required_in=ALL),
    # Notifications and push
    Setting("NOTIFICATION_DISPATCH_MODE", str, default="inline"),
    Setting("NOTIFICATION_BROADCAST_THRESHOLD", int, default=500),
    Setting("NOTIFICATION_UNREAD_COUNT_CACHE_TTL", int, default=60),
    Setting("FIREBASE_CREDENTIALS", str, default="", secret=True),
    Setting("PUSH_ENABLED", bool, default=True),
    # Celery beat
    Setting("BEAT_SCHEDULES", str, default="all"),
)
