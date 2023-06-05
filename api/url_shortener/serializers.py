from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.url_shortener import UrlShortener


class ShowShortenUrlsSerializer(ModelSerializer):
    longUrl = serializers.CharField(source="long_url")
    shortUrl = serializers.CharField(source="short_url")

    class Meta:
        model = UrlShortener

        fields = ["id", "title", "longUrl", "shortUrl"]
