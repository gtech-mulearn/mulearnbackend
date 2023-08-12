import re
import uuid

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.url_shortener import UrlShortener
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils


class ShowShortenUrlsSerializer(ModelSerializer):
    class Meta:
        model = UrlShortener

        fields = ["id", "title", "long_url", "short_url"]


class ShortenUrlsCreateUpdateSerializer(ModelSerializer):
    long_url = serializers.CharField(required=False)
    title = serializers.CharField(required=False)

    class Meta:
        model = UrlShortener
        fields = ("title", "long_url", "short_url")

    def create(self, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        validated_data['id'] = uuid.uuid4()
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        validated_data['created_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()

        return UrlShortener.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        instance.short_url = validated_data.get('short_url', instance.short_url)
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()

        instance.save()
        return instance

    def validate_short_url(self, value):
        special_characters_list = r'[~`!@#$%^&*()-+=|{}[\]:;"\'<>,?\\]'
        special_character = re.search(special_characters_list, value)

        if special_character or len(value) > 300:
            raise serializers.ValidationError("Your shortened URL should be less than 300 characters in length,"
                                              "only include letters, numbers and following special characters (/_)")
        return value
