from django.db.models import Q
from rest_framework import serializers

from db.integrations import Integration, IntegrationAuthorization
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
        user_ig_links = obj.user_ig_link_user.all()

        # Extract ig_ids for filtering KarmaActivityLog in one go
        interest_groups = [ig_link.ig for ig_link in user_ig_links]

        # Aggregate karma for each interest group in one query
        aggregated_karma = obj.karma_activity_log_user.all()

        aggregated_karma = [
            {
                "task__ig__id": karma.task.ig.id,
                "task__ig__name": karma.task.ig.name,
                "karma": karma.karma,
            }
            for karma in aggregated_karma
            if hasattr(karma.task, "ig") and karma.task.ig
        ]

        ig_details = {ig.name: 0 for ig in interest_groups}

        # Update the karma if a match is found
        for karma in aggregated_karma:
            ig_name = karma["task__ig__name"]
            if ig_name in ig_details:
                ig_details[ig_name] += karma["karma"]

        return ig_details

    def get_jsid(self, obj):
        return int(obj.jsid) if obj.jsid else None


class KKEMAuthorization(serializers.Serializer):
    emailOrMuid = serializers.CharField(write_only=True)
    param = serializers.CharField(write_only=True)

    email = serializers.CharField(read_only=True)
    fullname = serializers.CharField(read_only=True)
    mu_id = serializers.CharField(read_only=True)
    link_id = serializers.CharField(read_only=True)

    verified = serializers.BooleanField()

    class Meta:
        fields = (
            "emailOrMuid",
            "param",
            "verified",
            "email",
            "fullname",
            "mu_id",
            "link_id",
        )

    def to_representation(self, instance):
        return {
            "email": instance.user.email,
            "fullname": instance.user.fullname,
            "mu_id": instance.user.mu_id,
            "link_id": instance.id,
            "verified": instance.verified,
        }

    def validate(self, attrs):
        data = super().validate(attrs)
        details = kkem_helper.decrypt_kkem_data(data["param"])
        attrs["jsid"] = details["jsid"][0]
        attrs["dwms_id"] = details["dwms_id"][0]

        return attrs

    def create(self, validated_data):
        email_or_muid = validated_data["emailOrMuid"]
        user = self.verify_user(email_or_muid)

        integration = Integration.objects.get(name=IntegrationType.KKEM.value)
        jsid = validated_data["jsid"]
        dwms_id = validated_data["dwms_id"]

        kkem_link = self.get_kkem_link(user, integration, jsid)

        if kkem_link:
            if (
                self.context["type"] == "login"
                and kkem_link.integration_value == jsid
                and kkem_link.verified
            ):
                return kkem_link

            elif kkem_link.verified:
                raise ValueError(
                    "Your μLearn account is already connected to a KKEM account"
                )

            elif kkem_link.user == user:
                self.update_integration(validated_data, kkem_link)
            else:
                raise ValueError("Something went wrong")
        else:
            kkem_link = self.create_kkem_link(
                user, integration, dwms_id, jsid, validated_data["verified"]
            )
        if validated_data["verified"]:
            kkem_helper.send_data_to_kkem(kkem_link)

        return kkem_link

    def verify_user(self, user_mu_id):
        if user := User.objects.filter(
            Q(mu_id=user_mu_id) | Q(email=user_mu_id)
        ).first():
            return user
        else:
            raise ValueError(
                "Oops! We couldn't find that account. Please double-check your details and try again."
            )

    def get_kkem_link(self, user, integration, jsid):
        if kkem_link := IntegrationAuthorization.objects.filter(
            user=user, integration=integration
        ).first():
            return kkem_link
        if IntegrationAuthorization.objects.filter(
            integration_value=jsid, integration=integration
        ).exists():
            raise ValueError("This KKEM account is already connected to another user")

        return None

    def create_kkem_link(self, user, integration, dwms_id, jsid, verified):
        return IntegrationAuthorization.objects.create(
            integration=integration,
            user=user,
            additional_field=dwms_id,
            verified=verified,
            integration_value=jsid,
            created_at=DateTimeUtils.get_current_utc_time(),
            updated_at=DateTimeUtils.get_current_utc_time(),
        )

    def update_integration(self, validated_data, kkem_link):
        kkem_link.integration_value = validated_data["jsid"]
        kkem_link.updated_at = DateTimeUtils.get_current_utc_time()
        kkem_link.verified = validated_data["verified"]
        kkem_link.addition_field = validated_data["dwms_id"]
        kkem_link.save()
