from rest_framework import serializers
from django.db.models import Sum

from db.user import User
from db.organization import (
    Country,
    District,
    Organization,
    State,
)
from db.learning_circle import LearningCircle
from db.task import KarmaActivityLog
from db.user import User

class LcListSerializer(serializers.ModelSerializer):
    ig_name = serializers.CharField(source='ig.name')
    org_name = serializers.CharField(source='org.title', allow_null=True)
    member_count = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    lead_name = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()
    class Meta:
        model = LearningCircle
        fields = [
            'id',
            'name',
            'ig_name',
            'org_name',
            'member_count',
            'members',
            'meet_place',
            'meet_time',
            'lead_name',
            'karma'
        ]

    def get_lead_name(self, obj):
        user_circle_link = obj.user_circle_link_circle.filter(
            circle=obj,
            accepted=1,
            lead=True
        ).first()

        return user_circle_link.user.full_name if user_circle_link else None

    def get_member_count(self, obj):
        return obj.user_circle_link_circle.filter(
            circle=obj,
            accepted=1
        ).count()

    def get_members(self, obj):
        user_circle_link = obj.user_circle_link_circle.filter(
            circle=obj,
            accepted=1
        )

    def get_karma(self, obj):
        
        karma_activity_log = KarmaActivityLog.objects.filter(
            user__user_circle_link_user__circle=obj,
        ).aggregate(
            karma=Sum(
                'karma'
            )
        )['karma']

        return karma_activity_log if karma_activity_log else 0
    
class LcDetailsSerializer(serializers.ModelSerializer):
    college = serializers.CharField(source='org.title', allow_null=True)
    total_karma = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    ig_code = serializers.CharField(source='ig.code')
    ig_id = serializers.CharField(source='ig.id')
    ig_name = serializers.CharField(source='ig.name')

    class Meta:
        model = LearningCircle
        fields = [
            "name",
            "circle_code",
            "note",
            "day",
            "college",
            "members",
            "rank",
            "total_karma",
            "ig_id",
            "ig_name",
            "ig_code"
        ]

    def get_total_karma(self, obj):
        return (
            KarmaActivityLog.objects.filter(
                user__user_circle_link_user__circle=obj,
                user__user_circle_link_user__accepted=True,
                task__ig=obj.ig,
                appraiser_approved=True,
            ).aggregate(
                total_karma=Sum(
                    'karma'
                ))['total_karma'] or 0
        )

    def get_members(self, obj):
        return self._get_member_info(obj, accepted=1)


    def _get_member_info(self, obj, accepted):

        members = obj.user_circle_link_circle.filter(
            circle=obj,
            accepted=accepted
        )

        member_info = []

        for member in members:
            total_ig_karma = KarmaActivityLog.objects.filter(
                task__ig=member.circle.ig,
                user=member.user,
                appraiser_approved=True
            ).aggregate(
                total_karma=Sum(
                    'karma'
                ))['total_karma'] or 0

            member_info.append({
                'id': member.user.id,
                'username': f'{member.user.full_name}',
                'profile_pic': f'{member.user.profile_pic}' or None,
                'karma': total_ig_karma,
                'is_lead': member.lead,
                'level': member.user.user_lvl_link_user.level.level_order
            })

        return member_info

    def get_rank(self, obj):
        total_karma = KarmaActivityLog.objects.filter(
            user__user_circle_link_user__circle=obj,
            user__user_circle_link_user__accepted=True,
            task__ig=obj.ig,
            appraiser_approved=True
        ).aggregate(
            total_karma=Sum(
                'karma'
            )
        )['total_karma'] or 0

        circle_ranks = {obj.name: {'total_karma': total_karma}}

        all_learning_circles = LearningCircle.objects.filter(
            ig=obj.ig
        ).exclude(
            id=obj.id
        )

        for lc in all_learning_circles:
            total_karma_lc = KarmaActivityLog.objects.filter(
                user__user_circle_link_user__circle=lc,
                user__user_circle_link_user__accepted=True,
                task__ig=lc.ig,
                appraiser_approved=True
            ).aggregate(
                total_karma=Sum(
                    'karma'
                )
            )['total_karma'] or 0

            circle_ranks[lc.name] = {'total_karma': total_karma_lc}

        sorted_ranks = sorted(
            circle_ranks.items(),
            key=lambda x: x[1]['total_karma'],
            reverse=True
        )

        return next(
            (
                i + 1
                for i, (circle_name, data) in enumerate(sorted_ranks)
                if circle_name == obj.name
            ),
            None,
        )


class StudentInfoSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    muid = serializers.CharField()
    circle_name = serializers.CharField()
    circle_ig = serializers.CharField()
    organisation = serializers.CharField()
    dwms_id = serializers.CharField(allow_null=True)
    karma_earned = serializers.IntegerField()


class CollegeInfoSerializer(serializers.Serializer):
    org_title = serializers.CharField()
    learning_circle_count = serializers.CharField()
    user_count = serializers.CharField()


class LearningCircleEnrollmentSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    muid = serializers.CharField()
    email = serializers.CharField()
    dwms_id = serializers.CharField(allow_null=True)
    circle_name = serializers.CharField()
    circle_ig = serializers.CharField()
    organisation = serializers.CharField()
    district = serializers.CharField(allow_null=True)
    karma_earned = serializers.IntegerField()


class UserLeaderboardSerializer(serializers.ModelSerializer):
    interest_groups = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()
    karma = serializers.IntegerField(source="wallet_user.karma")
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'full_name',
            "karma",
            "interest_groups",
            "organizations",
        )

    def get_full_name(self, obj):
        return obj.full_name

    def get_organizations(self, obj):
        return obj.user_organization_link_user.all().values_list("org__title", flat=True)

    def get_interest_groups(self, obj):
        return obj.user_ig_link_user.all().values_list("ig__name", flat=True)



class OrgSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "title"]

class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ["id", "name"]

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name"]
class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name"]