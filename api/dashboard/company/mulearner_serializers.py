from rest_framework import serializers
from db.user import User

class MulearnerDirectorySerializer(serializers.ModelSerializer):
    karma = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    college = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    graduation_year = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'muid', 'email', 'karma', 'level', 
            'college', 'department', 'graduation_year'
        ]

    def get_karma(self, obj):
        # Uses annotated_karma from the queryset (Coalesce, no extra DB hit)
        annotated = getattr(obj, 'annotated_karma', None)
        if annotated is not None:
            return annotated
        try:
            return obj.wallet_user.karma
        except Exception:
            return 0

    def get_level(self, obj):
        # Uses select_related cache — no extra DB hit
        try:
            lvl_link = obj.user_lvl_link_user
            return lvl_link.level.level_order if lvl_link and lvl_link.level else 0
        except Exception:
            return 0

    def get_college(self, obj):
        # Uses prefetch_related cache — no extra DB hit
        try:
            for org_link in obj.user_organization_link_user.all():
                if org_link.org and org_link.org.org_type == 'College':
                    return org_link.org.title
            return None
        except Exception:
            return None

    def get_department(self, obj):
        # Uses prefetch_related cache — no extra DB hit
        try:
            for org_link in obj.user_organization_link_user.all():
                if org_link.org and org_link.org.org_type == 'College':
                    return org_link.department.title if org_link.department else None
            return None
        except Exception:
            return None

    def get_graduation_year(self, obj):
        # Uses prefetch_related cache — no extra DB hit
        try:
            for org_link in obj.user_organization_link_user.all():
                if org_link.org and org_link.org.org_type == 'College':
                    return org_link.graduation_year
            return None
        except Exception:
            return None
