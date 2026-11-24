from django.db.models import Q
from rest_framework import serializers

from db.integrations import Integration, IntegrationAuthorization
from db.user import User
from utils.exception import CustomException
from utils.types import IntegrationType
from utils.utils import DateTimeUtils

from . import kkem_helper


class KKEMUserSerializer(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()
    jsid = serializers.SerializerMethodField()
    mu_id = serializers.CharField(source="muid")

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
            obj.wallet_user.karma
            if hasattr(obj, "wallet_user") and hasattr(obj.wallet_user, "karma")
            else 0
        )
        return karma

    @staticmethod
    def ig_karma_by_user(user_ids, approved_only=True):
        """
        {user_id: {ig name: approved karma}} in one grouped query. It replaces
        loading every approved karma log (with task and IG) per user and
        summing in Python. Grouped by IG id and summed by exact name here, as
        the old loop did (two IGs sharing a name add up).

        approved_only=False counts every log: the individual endpoint read the
        user's unfiltered karma log, unlike the bulk one (kept as it was).
        """
        from django.db.models import Sum
        from db.task import KarmaActivityLog

        result = {}
        rows = (
            KarmaActivityLog.objects.filter(
                user_id__in=list(user_ids), task__ig__isnull=False,
                **({"appraiser_approved": True} if approved_only else {}),
            )
            .values_list("user_id", "task__ig_id", "task__ig__name")
            .annotate(total=Sum("karma"))
            .order_by()
        )
        for user_id, _, ig_name, total in rows:
            per_user = result.setdefault(user_id, {})
            per_user[ig_name] = per_user.get(ig_name, 0) + total
        return result

    def get_interest_groups(self, obj):
        if "user_ig_link_user" in getattr(obj, "_prefetched_objects_cache", {}):
            user_ig_links = obj.user_ig_link_user.all()
        else:
            user_ig_links = obj.user_ig_link_user.select_related("ig")
        interest_groups = [ig_link.ig for ig_link in user_ig_links]

        ig_karma = self.context.get("ig_karma")
        if ig_karma is None:
            # Individual endpoint: every log, as before (see ig_karma_by_user).
            ig_karma = self.ig_karma_by_user([obj.id], approved_only=False)
        user_karma = ig_karma.get(obj.id, {})

        # Only the IGs the user is linked to, in link order (as before).
        ig_details = {ig.name: 0 for ig in interest_groups}
        for ig_name in ig_details:
            ig_details[ig_name] += user_karma.get(ig_name, 0)

        return [{"name": key, "karma": value} for key, value in ig_details.items()]

    def get_jsid(self, obj):
        return int(obj.jsid) if obj.jsid else None


class KKEMAuthorization(serializers.Serializer):
    emailOrMuid = serializers.CharField(write_only=True)
    param = serializers.CharField(write_only=True)

    email = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    muid = serializers.CharField(read_only=True)
    link_id = serializers.CharField(read_only=True)

    verified = serializers.BooleanField()

    class Meta:
        fields = (
            "emailOrMuid",
            "param",
            "verified",
            "email",
            "full_name",
            "muid",
            "link_id",
        )

    def to_representation(self, instance):
        return {
            "email": instance.user.email,
            "full_name": instance.user.full_name,
            "muid": instance.user.muid,
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
                raise CustomException(
                    "Your μLearn account is already connected to a KKEM account"
                )

            elif kkem_link.user == user:
                self.update_integration(validated_data, kkem_link)
            else:
                raise CustomException("Something went wrong")
        else:
            kkem_link = self.create_kkem_link(
                user, integration, dwms_id, jsid, validated_data["verified"]
            )
        if validated_data["verified"]:
            kkem_helper.send_data_to_kkem(kkem_link)

        return kkem_link

    def verify_user(self, user_muid):
        if user := User.objects.filter(Q(muid=user_muid) | Q(email=user_muid)).first():
            return user
        else:
            raise CustomException(
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
            raise CustomException(
                "This KKEM account is already connected to another user")

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
