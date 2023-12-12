from django.db import models


class ActiveUserManager(models.Manager):
    def get_queryset(self):
        # This will return only the users where suspended_at, and suspended_by are NULL
        return (
            super()
            .get_queryset()
            .filter(
                suspended_at__isnull=True,
                suspended_by__isnull=True,
            )
        )
