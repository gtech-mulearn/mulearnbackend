# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

from rest_framework.serializers import Serializer
from rest_framework.exceptions import ValidationError

original_to_internal_value = Serializer.to_internal_value

def strict_to_internal_value(self, data):
    if isinstance(data, dict):
        unknown_keys = set(data.keys()) - set(self.fields.keys())
        if unknown_keys:
            errors = {key: ["Unknown field."] for key in unknown_keys}
            raise ValidationError(errors)
            
    return original_to_internal_value(self, data)

Serializer.to_internal_value = strict_to_internal_value

__all__ = ("celery_app",)
