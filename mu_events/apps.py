from django.apps import AppConfig


class MuEventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mu_events"

    def ready(self):
        from mu_events import signals  # noqa: F401 — connects the receivers
