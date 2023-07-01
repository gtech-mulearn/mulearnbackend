from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.url_shortener import UrlShortener


class ShowShortenUrlsSerializer(ModelSerializer):

    class Meta:
        model = UrlShortener

        fields = ["id", "title", "long_url", "short_url"]
