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
        try:
            return obj.wallet_user.karma
        except Exception:
            return 0

    def get_level(self, obj):
        try:
            return obj.user_lvl_link_user.level.level_order
        except Exception:
            return 0

    def get_college(self, obj):
        try:
            org_link = obj.user_organization_link_user.filter(org__org_type='College').first()
            return org_link.org.title if org_link else None
        except Exception:
            return None

    def get_department(self, obj):
        try:
            org_link = obj.user_organization_link_user.filter(org__org_type='College').first()
            return org_link.department.title if org_link and org_link.department else None
        except Exception:
            return None

    def get_graduation_year(self, obj):
        try:
            org_link = obj.user_organization_link_user.filter(org__org_type='College').first()
            return org_link.graduation_year if org_link else None
        except Exception:
            return None
