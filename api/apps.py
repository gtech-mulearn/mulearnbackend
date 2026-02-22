from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # Register drf-spectacular schema extensions for Events & Campus APIs
        from utils.swagger_schemas import (
            apply_event_schema_extensions,
            apply_campus_schema_extensions,
        )
        apply_event_schema_extensions()
        apply_campus_schema_extensions()

