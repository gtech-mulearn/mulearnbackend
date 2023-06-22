from rest_framework import serializers
from django.db.models import Sum
from db.integrations import KKEMAuthorization
from db.task import KarmaActivityLog, UserIgLink

from db.user import User


class KKEMBulkKarmaSerializer(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()
    dwms_id = serializers.SerializerMethodField()

    def get_total_karma(self, obj):
        karma = obj.total_karma_user.karma if hasattr(obj, "total_karma_user") else 0
        return karma

    def get_interest_groups(self, obj):
        interest_groups = []
        for ig_link in UserIgLink.objects.filter(user=obj):
            total_ig_karma = (
                0
                if KarmaActivityLog.objects.filter(task__ig=ig_link.ig, created_by=obj)
                .aggregate(Sum("karma"))
                .get("karma__sum")
                is None
                else KarmaActivityLog.objects.filter(
                    task__ig=ig_link.ig, created_by=obj
                )
                .aggregate(Sum("karma"))
                .get("karma__sum")
            )
            interest_groups.append({"name": ig_link.ig.name, "karma": total_ig_karma})
        return interest_groups

    def get_dwms_id(self, obj):
        return KKEMAuthorization.objects.filter(user=obj, verified=True).first().dwms_id

    class Meta:
        model = User
        fields = [
            "mu_id",
            "dwms_id",
            "total_karma",
            "interest_groups",
        ]
