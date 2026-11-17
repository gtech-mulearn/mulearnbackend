from datetime import timedelta

from django.db.models import Count, Q, Sum
from rest_framework import serializers

from db.learning_circle import LearningCircle
from db.organization import College, UserOrganizationLink, Organization, Department
from db.task import KarmaActivityLog
from utils.types import RoleType, OrganizationType
from utils.utils import DateTimeUtils


class CollegeListSerializer(serializers.ModelSerializer):
    """
    Every figure below is computed for the whole page in one grouped query (see
    _page_stats) instead of per college. The list endpoint is unauthenticated
    and used to run about seven queries per row, i.e. ~7,000 for perPage=1000.
    """

    org = serializers.CharField(source="org.title")
    number_of_members = serializers.SerializerMethodField()
    total_karma = serializers.SerializerMethodField()
    no_of_lc = serializers.SerializerMethodField()
    no_of_alumni = serializers.SerializerMethodField()

    class Meta:
        model = College
        fields = [
            "id",
            "level",
            "org",
            "number_of_members",
            "total_karma",
            "no_of_lc",
            "no_of_alumni",
        ]

    def _page_stats(self):
        """Per-org figures for every college being serialized, built once."""
        if getattr(self, "_stats", None) is not None:
            return self._stats

        instance = self.root.instance
        colleges = [instance] if isinstance(instance, College) else list(instance or [])
        org_ids = [college.org_id for college in colleges]
        since = DateTimeUtils.get_current_utc_time() - timedelta(days=30)
        recent = Q(created_at__gte=since)

        verified_links = UserOrganizationLink.objects.filter(
            org_id__in=org_ids, verified=True
        )

        members = {
            row["org_id"]: row
            for row in verified_links.values("org_id").annotate(
                total=Count("user", distinct=True),
                recent=Count("user", distinct=True, filter=recent),
            )
        }

        alumni = dict(
            verified_links.filter(
                org__org_type=OrganizationType.COLLEGE.value,
                user__user_role_link_user__role__title=RoleType.STUDENT.value,
                is_alumni=True,
            )
            .values_list("org_id")
            .annotate(total=Count("id"))
        )

        circles = {
            row["org_id"]: row
            for row in LearningCircle.objects.filter(org_id__in=org_ids)
            .values("org_id")
            .annotate(total=Count("id"), recent=Count("id", filter=recent))
        }

        # Karma: sum each member's approved karma once, then credit it to their
        # college(s). Going through (org, user) pairs keeps the old "user IN
        # (verified members)" meaning, where a user with two links to the same
        # college is still counted once.
        college_links = verified_links.filter(
            org__org_type=OrganizationType.COLLEGE.value
        )
        orgs_by_user = {}
        for org_id, user_id in college_links.values_list("org_id", "user_id").distinct():
            orgs_by_user.setdefault(user_id, set()).add(org_id)
        karma = {}
        if orgs_by_user:
            per_user = (
                KarmaActivityLog.objects.filter(
                    user_id__in=college_links.values("user_id"),
                    appraiser_approved=True,
                )
                .values_list("user_id")
                .annotate(total=Sum("karma"), recent=Sum("karma", filter=recent))
            )
            for user_id, total, recent_total in per_user:
                for org_id in orgs_by_user.get(user_id, ()):
                    entry = karma.setdefault(org_id, [0, 0])
                    entry[0] += total or 0
                    entry[1] += recent_total or 0

        self._stats = {
            "members": members,
            "alumni": alumni,
            "circles": circles,
            "karma": karma,
        }
        return self._stats

    def get_no_of_alumni(self, obj):
        return self._page_stats()["alumni"].get(obj.org_id, 0)

    def get_no_of_lc(self, obj):
        row = self._page_stats()["circles"].get(obj.org_id, {})
        return {
            'lc_count': row.get("total", 0),
            'no_of_lc_increased': row.get("recent", 0),
        }

    def get_number_of_members(self, obj):
        row = self._page_stats()["members"].get(obj.org_id, {})
        return {
            'member_count': row.get("total", 0),
            'no_of_members_increased': row.get("recent", 0),
        }

    def get_total_karma(self, obj):
        total_karma_gained, total_karma_increased = self._page_stats()["karma"].get(
            obj.org_id, (0, 0)
        )
        if total_karma_gained:
            increased_percentage = (total_karma_increased / total_karma_gained) * 100
        else:
            increased_percentage = 0
        return {'total_karma_gained': total_karma_gained, 'total_karma_increased': total_karma_increased,
                'increased_percentage': increased_percentage}


class CollegeChangeSerializer(serializers.Serializer):
    org_id = serializers.CharField(max_length=36, required=True)
    department_id = serializers.CharField(max_length=36, required=False, allow_null=True)

    def validate_org_id(self, value):
        if not Organization.objects.filter(
            id=value,
            org_type=OrganizationType.COLLEGE.value
        ).exists():
            raise serializers.ValidationError("Invalid organization ID provided")
        return value

    def validate_department_id(self, value):
        if value and not Department.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid department ID provided")
        return value
