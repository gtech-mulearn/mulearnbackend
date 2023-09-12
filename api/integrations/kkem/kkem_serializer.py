import json
from django.db.models import Q
from django.db.models import Sum
from django.db.utils import IntegrityError
import requests
from rest_framework import serializers

from db.integrations import IntegrationAuthorization, Integration
from db.task import KarmaActivityLog, UserIgLink
from db.user import User
from utils.types import IntegrationType
from utils.utils import DateTimeUtils
from . import kkem_helper


class KKEMUserSerializer(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()
    jsid = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "mu_id",
            "email",
            "jsid",
            "total_karma",
            "interest_groups",
        ]

    def get_total_karma(self, obj):
        karma = (
            obj.total_karma_user.karma
            if hasattr(obj, "total_karma_user")
            and hasattr(obj.total_karma_user, "karma")
            else 0
        )
        return karma

    def get_interest_groups(self, obj):
        interest_groups = []
        for ig_link in UserIgLink.objects.filter(user=obj):
            total_ig_karma = (
                0
                if KarmaActivityLog.objects.filter(task__ig=ig_link.ig, user=obj)
                .aggregate(Sum("karma"))
                .get("karma__sum")
                is None
                else KarmaActivityLog.objects.filter(task__ig=ig_link.ig, user=obj)
                .aggregate(Sum("karma"))
                .get("karma__sum")
            )
            interest_groups.append({"name": ig_link.ig.name, "karma": total_ig_karma})
        return interest_groups

    def get_jsid(self, obj):
        return int(
            IntegrationAuthorization.objects.get(
                user=obj, verified=True, integration__name=IntegrationType.KKEM.value
            ).integration_value
        )


class KKEMAuthorization(serializers.ModelSerializer):
    emailOrMuid = serializers.CharField(source="user.mu_id")
    param = serializers.CharField(write_only=True)

    class Meta:
        model = IntegrationAuthorization
        fields = ("emailOrMuid", "param", "verified")

    def validate(self, attrs):
        data = super().validate(attrs)
        details = kkem_helper.decrypt_kkem_data(data["param"])
        attrs["integration_value"] = details
        return attrs

    def create(self, validated_data):
        user_mu_id = validated_data["user"]["mu_id"]

        user = self.verify_user(user_mu_id)
        integration = Integration.objects.get(name=IntegrationType.KKEM.value)

        try:
            dwms_id = validated_data["integration_value"]["dwms_id"][0]
            jsid = validated_data["integration_value"]["jsid"][0]

            kkem_link = IntegrationAuthorization.objects.create(
                integration=integration,
                user=user,
                additional_field=dwms_id,
                verified=validated_data["verified"],
                integration_value=jsid,
                created_at=DateTimeUtils.get_current_utc_time(),
                updated_at=DateTimeUtils.get_current_utc_time(),
            )

        except Exception as e:
            jsid = validated_data["integration_value"]["jsid"][0]

            kkem_link = IntegrationAuthorization.objects.filter(
                user=user, integration=integration
            ).first()

            if (
                not kkem_link
                and IntegrationAuthorization.objects.filter(
                    integration_value=jsid,
                    integration=integration,
                ).first()
            ):
                raise ValueError(
                    "This KKEM account is already connected to another user"
                ) from e
            elif (
                self.context["type"] == "login"
                and kkem_link.integration_value == jsid
                and kkem_link.verified == True
            ):
                return kkem_link
            elif kkem_link.verified:
                raise ValueError(
                    "Your μLearn account is already connected to a KKEM account"
                ) from e
            elif kkem_link.user == user:
                self.update_integration(validated_data, kkem_link)
            else:
                raise ValueError("Something went wrong") from e

        return {
            "email": kkem_link.user.email,
            "fullname": kkem_link.user.fullname,
            "mu_id": kkem_link.user.mu_id,
            "link_id": kkem_link.id,
        }

    def verify_user(self, user_mu_id):
        if not (
            user := User.objects.filter(
                Q(mu_id=user_mu_id) | Q(email=user_mu_id)
            ).first()
        ):
            raise ValueError("User doesn't exist")
        return user

    def update_integration(self, validated_data, kkem_link):
        kkem_link.integration_value = validated_data["integration_value"]["jsid"][0]
        kkem_link.updated_at = DateTimeUtils.get_current_utc_time()
        kkem_link.verified = validated_data["verified"]
        kkem_link.addition_field = validated_data["integration_value"]["dwms_id"][0]
        kkem_link.save()
