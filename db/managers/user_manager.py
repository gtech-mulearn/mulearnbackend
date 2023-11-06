from django.db import models


class ActiveUserManager(models.Manager):
    def get_queryset(self):
        # This will return only the users where deleted_at, deleted_by, suspended_at, and suspended_by are NULL
        return (
            super()
            .get_queryset()
            .filter(
                deleted_at__isnull=True,
                deleted_by__isnull=True,
                suspended_at__isnull=True,
                suspended_by__isnull=True,
            )
        )
