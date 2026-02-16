from rest_framework import serializers

from db.user import User


class ExternalUserDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer for external API to fetch basic public user details.
    
    This serializer is specifically designed for external website integration,
    returning only non-sensitive public information about users.
    
    Excludes: email, mobile, password, and other sensitive fields
    """
    interest_groups = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()
    karma = serializers.IntegerField(source="wallet_user.karma", default=0)

    class Meta:
        model = User
        fields = (
            "full_name",
            "muid",
            "interest_groups",
            "organizations",
            "profile_pic",
            "karma",
        )

    def get_organizations(self, obj):
        """
        Get list of organizations the user is affiliated with.
        
        Returns organization id, title, code, and type.
        """
        org_links = (
            obj.user_organization_link_user.all()
            .select_related("org")
            .only("org__id", "org__title", "org__code", "org__org_type")
        )
        data = []
        for org_link in org_links:
            data.append(
                {
                    "id": org_link.org.id,
                    "title": org_link.org.title,
                    "code": org_link.org.code,
                    "org_type": org_link.org.org_type,
                }
            )
        return data

    def get_interest_groups(self, obj):
        """
        Get list of interest groups the user belongs to.
        
        Returns interest group id and name.
        """
        ig_links = (
            obj.user_ig_link_user.all().select_related("ig").only("ig__id", "ig__name")
        )
        data = []
        for ig_link in ig_links:
            data.append({"id": ig_link.ig.id, "name": ig_link.ig.name})
        return data
