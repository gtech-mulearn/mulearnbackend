from django.db import models
from db.user import User


class UrlShortener(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    long_url = models.CharField(max_length=2000, blank=True, null=True)
    short_url = models.CharField(max_length=300, blank=True, null=True)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by', blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'url_shortener'