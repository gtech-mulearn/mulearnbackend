from django.db import models

from db.user import User


class UrlShortener(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=100)
    short_url = models.CharField(unique=True, max_length=100)
    long_url = models.CharField(max_length=500)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by',
                                   related_name='url_shortener_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by',
                                   related_name='url_shortener_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'url_shortener'
