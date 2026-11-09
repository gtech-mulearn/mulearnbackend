from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        # Signal receivers register on import (spec A §3.7).
        from api.email_verification import signals  # noqa: F401
        from api.integrations.partner_sso import signals as partner_sso_signals  # noqa: F401
