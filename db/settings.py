from django.db import models

from db.user import User

# fmt: off
# noinspection PyPep8

class Device(models.Model):
    id          = models.CharField(primary_key=True, max_length=36)
    browser     = models.CharField(max_length=36, null=False)
    os          = models.CharField(max_length=36, null=False)
    user_id     = models.ForeignKey(User, on_delete=models.CASCADE)
    last_log_in = models.DateTimeField(null=False)

    class Meta:
        managed = False
        db_table = "device"


class SystemSetting(models.Model):
    key         = models.CharField(primary_key=True, max_length=100)
    value       = models.CharField(max_length=100)
    updated_at  = models.DateTimeField()
    created_at  = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "system_setting"