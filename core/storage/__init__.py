from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    location = settings.MEDIAFILES_LOCATION
    custom_domain = False
    default_acl = "private"


class StaticStorage(S3Boto3Storage):
    location = settings.STATICFILES_LOCATION
    custom_domain = False
    default_acl = "public-read"


class PublicStorage(S3Boto3Storage):
    location = settings.PUBLIC_STORAGE_LOCATION
    custom_domain = False
    default_acl = "public-read"
