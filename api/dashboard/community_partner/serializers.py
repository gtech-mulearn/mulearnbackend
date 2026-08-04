"""
Serializers for the Community Partner module.

Read serializer  — returned in GET responses; embeds linked IGs.
Write serializer — used for POST (create) and PATCH (partial update); validates
                    the `interest_groups` id list against real InterestGroup rows.
"""
from rest_framework import serializers

from db.community_partner import CommunityPartner, IgCommunityPartnerLink
from db.task import InterestGroup


class CommunityPartnerReadSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Community Partners.

    `logo_key` is returned as-is (a plain string) rather than resolved to a
    URL — there is no upload/storage backing it yet (S3 is not functional).
    """
    interest_groups = serializers.SerializerMethodField()

    class Meta:
        model = CommunityPartner
        fields = [
            'id',
            'name',
            'logo_key',
            'description',
            'linkedin',
            'github',
            'website',
            'instagram',
            'interest_groups',
            'created_at',
            'updated_at',
        ]

    def get_interest_groups(self, obj):
        links = IgCommunityPartnerLink.objects.filter(
            community_partner=obj
        ).select_related('interest_group')
        return [
            {
                'id': link.interest_group.id,
                'name': link.interest_group.name,
                'code': link.interest_group.code,
            }
            for link in links
        ]


class CommunityPartnerWriteSerializer(serializers.Serializer):
    """
    Write serializer for Community Partners (POST / PATCH).
    """
    name            = serializers.CharField(max_length=150)
    logo_key        = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    description     = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    linkedin        = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    github          = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    website         = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    instagram       = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    interest_groups = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )

    def validate_interest_groups(self, value):
        """`value` is a list of interest_group ids. Every id must resolve to
        an existing InterestGroup."""
        if not value:
            return value
        found_ids = set(
            InterestGroup.objects.filter(id__in=value).values_list('id', flat=True)
        )
        unknown_ids = [ig_id for ig_id in value if ig_id not in found_ids]
        if unknown_ids:
            raise serializers.ValidationError(
                f"Unknown interest group id(s): {', '.join(unknown_ids)}."
            )
        return value
