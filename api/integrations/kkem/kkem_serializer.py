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


class KKEMUserSerializer(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()
    jsid = serializers.SerializerMethodField()

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
        return IntegrationAuthorization.objects.get(
            user=obj, verified=True
        ).integration_value

    class Meta:
        model = User
        fields = [
            "mu_id",
            "jsid",
            "total_karma",
            "interest_groups",
        ]


class KKEMAuthorization(serializers.ModelSerializer):
    emailOrMuid = serializers.CharField(source="user.mu_id")

    def create(self, validated_data):
        user_mu_id = validated_data["user"]["mu_id"]

        integration = Integration.objects.get(name=IntegrationType.KKEM.value)
        self.integration = integration

        response = requests.post(
            url="https://stagging.knowledgemission.kerala.gov.in/MuLearn/api/jobseeker-details",
            data=f'{{"job_seeker_id": {validated_data["integration_value"]}}}',
            headers={"Authorization": f"Bearer {self.integration.token}"},
        )
        response_data = response.json()

        if "response" not in response_data or not response_data["response"].get("req_status", False):
            raise ValueError("Provided jsid is invalid")

        if not (
            user := User.objects.filter(
                Q(mu_id=user_mu_id) | Q(email=user_mu_id)
            ).first()
        ):
            raise ValueError("User doesn't exist")

        try:
            kkem_link = IntegrationAuthorization.objects.create(
                integration=self.integration,
                user=user,
                verified=validated_data["verified"],
                integration_value=validated_data["integration_value"],
                created_at=DateTimeUtils.get_current_utc_time(),
                updated_at=DateTimeUtils.get_current_utc_time(),
            )

        except IntegrityError as e:
            kkem_link = IntegrationAuthorization.objects.filter(
                user=user, integration=self.integration
            ).first()

            if (
                not kkem_link
                and IntegrationAuthorization.objects.filter(
                    integration_value=validated_data["integration_value"],
                    integration=self.integration,
                ).first()
            ):
                raise ValueError(
                    "This KKEM account is already connected to another user"
                ) from e
            elif (
                self.context["type"] == "login"
                and kkem_link.integration_value == validated_data["integration_value"]
                and kkem_link.verified == True
            ):
                return kkem_link
            elif kkem_link.verified:
                raise ValueError(
                    "Your μLearn account is already connected to a KKEM account"
                ) from e
            elif kkem_link.user == user:
                kkem_link.integration_value = validated_data["integration_value"]
                kkem_link.updated_at = DateTimeUtils.get_current_utc_time()
                kkem_link.verified = validated_data["verified"]
                kkem_link.save()
            else:
                raise ValueError("Something went wrong") from e

        return {
            "email": kkem_link.user.email,
            "fullname": kkem_link.user.fullname,
            "mu_id": kkem_link.user.mu_id,
            "link_id": kkem_link.id,
        }

    class Meta:
        model = IntegrationAuthorization
        fields = ["emailOrMuid", "integration_value", "verified"]
