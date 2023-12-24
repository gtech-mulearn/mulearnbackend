from django.apps import AppConfig
from decouple import config


class SystemUserNotFoundError(Exception):
    pass


class DbConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "db"

    def ready(self) -> None:
        _ready = super().ready()
        self.check_system_user_exists()
        return _ready

    @classmethod
    def check_system_user_exists(cls):
        from db.user import User
        if not User.objects.filter(id=config("SYSTEM_ADMIN_ID")).exists():
            raise SystemUserNotFoundError(
                f"Create a System User with pk -\"{config('SYSTEM_ADMIN_ID')}\""
            )
