import logging

from django.apps import AppConfig
from django.db import OperationalError
from decouple import config

logger = logging.getLogger("django")


class SystemUserNotFoundError(Exception):
    pass


class DbConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "db"

    def ready(self) -> None:
        # Models are registered via db/models.py, which Django imports
        # automatically during app population (before ready() runs).
        _ready = super().ready()
        self.check_system_user_exists()
        return _ready

    @classmethod
    def check_system_user_exists(cls):
        from db.organization import District as _
        from db.user import User
        try:
            exists = User.objects.filter(id=config("SYSTEM_ADMIN_ID")).exists()
        except OperationalError:
            # The database being unreachable at import time must not stop the
            # process from booting. It previously did, and combined with
            # `restart: always` that turned a saturated database into a
            # crash-loop which kept hammering it and prevented recovery.
            # A genuinely missing system user is still caught on the next boot
            # once the database is reachable.
            #
            # Deliberately narrower than `DatabaseError`: that base class also
            # covers `ProgrammingError` (missing table/column - a broken schema,
            # not a transient outage), which should still fail loudly instead of
            # letting the app boot against a schema that was never migrated.
            logger.exception(
                "Could not verify SYSTEM_ADMIN_ID at startup - database unreachable. "
                "Continuing boot; the check will run again on next start."
            )
            return
        if not exists:
            raise SystemUserNotFoundError(
                f"Create a System User with pk -\"{config('SYSTEM_ADMIN_ID')}\""
            )
