from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # Registers the model signal receivers in every process, Celery workers included.
        from api.common import signals  # noqa: F401
