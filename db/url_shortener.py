from django.db import models

from db.user import User

# fmt: off

class UrlShortener(models.Model):
    id               = models.CharField(primary_key=True, max_length=36)
    title            = models.CharField(max_length=100)
    short_url        = models.CharField(unique=True, max_length=100)
    long_url         = models.CharField(max_length=500)
    count            = models.IntegerField(blank=True, null=True, default=0)
    updated_by       = models.ForeignKey(User, on_delete=models.CASCADE, db_column='updated_by', related_name='url_shortener_updated_by')
    updated_at       = models.DateTimeField()
    created_by       = models.ForeignKey(User, on_delete=models.CASCADE, db_column='created_by', related_name='url_shortener_created_by')
    created_at       = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'url_shortener'


class UrlShortenerTracker(models.Model):
    id               = models.CharField(primary_key=True, max_length=36)
    ip_address       = models.CharField(max_length=45)
    browser          = models.CharField(max_length=255, blank=True, null=True)
    operating_system = models.CharField(max_length=255, blank=True, null=True)
    version          = models.CharField(max_length=255, blank=True, null=True)
    created_at       = models.DateTimeField(blank=True, null=True)
    device_type      = models.CharField(max_length=255, blank=True, null=True)
    url_shortener    = models.ForeignKey(UrlShortener, on_delete=models.CASCADE, blank=True, null=True)
    city             = models.CharField(max_length=36, blank=True, null=True)
    region           = models.CharField(max_length=36, blank=True, null=True)
    country          = models.CharField(max_length=36, blank=True, null=True)
    location         = models.CharField(max_length=36, blank=True, null=True)
    referrer         = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'url_shortener_tracker'
