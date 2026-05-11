from django.apps import AppConfig
from decouple import config


class SystemUserNotFoundError(Exception):
    pass


class DbConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "db"

    def ready(self) -> None:
        # Ensure all model modules are imported so Django's app registry
        # can resolve lazy string FK references like 'db.InterestGroup', 'db.Event'
        from db import task as _task          # noqa: F401 — registers InterestGroup etc.
        from db import mentor as _mentor      # noqa: F401 — registers MentorshipSession etc.
        from db import events as _events      # noqa: F401 — registers Event model
        _ready = super().ready()
        self.check_system_user_exists()
        return _ready

    @classmethod
    def check_system_user_exists(cls):
        from db.organization import District as _
        from db.user import User
        if not User.objects.filter(id=config("SYSTEM_ADMIN_ID")).exists():
            raise SystemUserNotFoundError(
                f"Create a System User with pk -\"{config('SYSTEM_ADMIN_ID')}\""
            )
