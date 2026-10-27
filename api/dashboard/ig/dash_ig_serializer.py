from rest_framework import serializers
import json
from datetime import date

from db.task import InterestGroup
from db.user import User, Socials


def _resolve_muid_list(muid_list, user_map=None, socials_map=None):
    """
    Given a list like [{"muid": "foo@mulearn"}, ...], fetch each user's
    details (including socials) from the DB and return an enriched list:
    [
        {
            "muid": "foo@mulearn",
            "full_name": "Foo Bar",
            "email": "foo@example.com",
            "profile_pic": "https://...",   # or null
            "socials": {
                "github": "...",
                "linkedin": "...",
                ...                          # null for unset fields
            }
        },
        ...
    ]
    MUIDs that don't match any User are included with null for extra fields.
    """
    if not isinstance(muid_list, list):
        return muid_list

    muids = [item.get("muid") for item in muid_list if isinstance(item, dict) and item.get("muid")]

    if not muids:
        return muid_list

    if user_map is None:
        # Batch-fetch users
        user_objs = User.objects.filter(muid__in=muids)
        user_map = {u.muid: u for u in user_objs}

    if socials_map is None:
        # Batch-fetch socials keyed by user_id
        user_ids = [u.id for u in user_map.values() if u]
        socials_qs = Socials.objects.filter(user_id__in=user_ids).values(
            "user_id", "github", "facebook", "instagram", "linkedin",
            "dribble", "behance", "stackoverflow", "medium", "hackerrank"
        )
        socials_map = {s["user_id"]: s for s in socials_qs}

    enriched = []
    for item in muid_list:
        if not isinstance(item, dict):
            enriched.append(item)
            continue

        muid = item.get("muid")
        user = user_map.get(muid)

        if user:
            raw_socials = socials_map.get(user.id)
            socials = {
                "github":        raw_socials.get("github")        if raw_socials else None,
                "facebook":      raw_socials.get("facebook")      if raw_socials else None,
                "instagram":     raw_socials.get("instagram")     if raw_socials else None,
                "linkedin":      raw_socials.get("linkedin")      if raw_socials else None,
                "dribble":       raw_socials.get("dribble")       if raw_socials else None,
                "behance":       raw_socials.get("behance")       if raw_socials else None,
                "stackoverflow": raw_socials.get("stackoverflow") if raw_socials else None,
                "medium":        raw_socials.get("medium")        if raw_socials else None,
                "hackerrank":    raw_socials.get("hackerrank")    if raw_socials else None,
            }

            enriched.append({
                "muid":        muid,
                "full_name":   user.full_name,
                "email":       user.email,
                "profile_pic": user.profile_pic,
                "socials":     socials,
            })
        else:
            # muid not found — include as-is with null details
            enriched.append({
                "muid": muid,
                "full_name": None,
                "email": None,
                "profile_pic": None,
            })

    return enriched


def _resolve_ig_mentors(ig, mentor_links=None, mentor_socials_map=None, mentor_profiles_map=None):
    """
    Active IG mentors for this IG, read from UserIgLink (authoritative)
    rather than the legacy InterestGroup.mentors JSON column, enriched with
    the same shape _resolve_muid_list produces plus the mentor's company.
    """
    from db.task import UserIgLink
    from api.dashboard.mentor.dash_mentor_helper import get_mentor_company
    from db.user import UserMentor

    if mentor_links is None:
        links = UserIgLink.objects.filter(
            ig=ig,
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            is_active=True,
        ).select_related("user")
    else:
        links = mentor_links

    user_ids = [link.user_id for link in links]
    if mentor_socials_map is None:
        socials_qs = Socials.objects.filter(user_id__in=user_ids).values(
            "user_id", "github", "facebook", "instagram", "linkedin",
            "dribble", "behance", "stackoverflow", "medium", "hackerrank"
        )
        mentor_socials_map = {s["user_id"]: s for s in socials_qs}

    if mentor_profiles_map is None:
        mentor_profiles = {
            m.user_id: m
            for m in UserMentor.objects.filter(user_id__in=user_ids)
        }
    else:
        mentor_profiles = mentor_profiles_map

    from db.user import MentorApplication
    applications = {
        a.user_id: a
        for a in MentorApplication.objects.filter(
            user_id__in=user_ids,
            status=MentorApplication.Status.APPROVED,
        ).select_related("org")
    }

    mentors = []
    for link in links:
        user = link.user
        raw_socials = mentor_socials_map.get(user.id)
        socials = {
            key: (raw_socials.get(key) if raw_socials else None)
            for key in ["github", "facebook", "instagram", "linkedin",
                        "dribble", "behance", "stackoverflow", "medium", "hackerrank"]
        }
        application = applications.get(user.id)
        mentors.append({
            "muid": user.muid,
            "full_name": user.full_name,
            "email": user.email,
            "profile_pic": user.profile_pic,
            "company": get_mentor_company(application) if application else None,
            "socials": socials,
        })
    return mentors


from api.dashboard.ig.impact_project_serializer import ImpactProjectSerializer


class InterestGroupSerializer(serializers.ModelSerializer):

    updated_by = serializers.CharField(source="updated_by.full_name")
    created_by = serializers.CharField(source="created_by.full_name")
    members = serializers.SerializerMethodField()
    cover_image = serializers.CharField(read_only=True, allow_null=True)
    icon_image = serializers.CharField(read_only=True, allow_null=True)
    category = serializers.ChoiceField(
        choices=["maker", "coder", "creative", "manager", "others"]
    )
    status = serializers.ChoiceField(
        choices=["active", "inactive", "requested", "cancelled", "rejected"]
    )
    impact_projects = ImpactProjectSerializer(
        source="impact_project_ig",
        many=True,
        read_only=True
    )
    media_content_links = serializers.SerializerMethodField()
    is_sponsored = serializers.SerializerMethodField()
    sponsor_company_name = serializers.SerializerMethodField()
    sponsor_company_logo = serializers.SerializerMethodField()
    community_partners = serializers.SerializerMethodField()

    class Meta:
        model = InterestGroup
        fields = [
            "id",
            "name",
            "resource",
            "about",
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
            "thinktank",
            "office_hours",
            "icon",
            "icon_image",
            "cover_image",
            "code",
            "category",
            "status",
            "members",
            "media_content_links",
            "is_sponsored",
            "sponsor_company_name",
            "sponsor_company_logo",
            "community_partners",
            "updated_by",
            "updated_at",
            "created_by",
            "created_at",
            "impact_projects",
        ]

    def get_members(self, obj):
        if hasattr(obj, "members"):
            return obj.members
        return obj.user_ig_link_ig.all().count()

    def get_media_content_links(self, obj):
        """
        Media content (e.g. Office Hours sessions) linked to this IG via
        ig_media_content_link, excluding soft-deleted media content.
        Only upcoming and ongoing (today) content is included.
        """
        today = date.today()
        links = obj.media_content_links.filter(
            media_content__deleted_at__isnull=True,
            media_content__date__gte=today,
        ).select_related("media_content").order_by("media_content__date")

        return [
            {
                "id": link.id,
                "media_content_id": link.media_content_id,
                "content_type": link.media_content.content_type,
                "title": link.media_content.title,
                "date": link.media_content.date,
                "link": link.media_content.link,
                "status": "ongoing" if link.media_content.date == today else "upcoming",
            }
            for link in links
        ]

    def get_community_partners(self, obj):
        """
        Community partners linked to this IG via ig_community_partner_link.
        """
        links = obj.community_partner_links.select_related("community_partner")
        return [
            {
                "id": link.community_partner.id,
                "name": link.community_partner.name,
                "logo_key": link.community_partner.logo_key,
                "description": link.community_partner.description,
                "linkedin": link.community_partner.linkedin,
                "github": link.community_partner.github,
                "website": link.community_partner.website,
                "instagram": link.community_partner.instagram,
            }
            for link in links
        ]

    def get_is_sponsored(self, obj):
        return obj.sponsor_status == "approved" and obj.sponsor_company_id is not None

    def get_sponsor_company_name(self, obj):
        return obj.sponsor_company.name if self.get_is_sponsored(obj) else None

    def get_sponsor_company_logo(self, obj):
        return obj.sponsor_company.logo if self.get_is_sponsored(obj) else None

    def to_representation(self, instance):
        """Convert JSON-serialized text fields back to Python objects for API output.
        For 'leads' and 'mentors', further enrich with user details from DB."""
        data = super().to_representation(instance)

        # Plain JSON fields — just parse the string back to Python
        plain_json_fields = [
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
        ]

        for field in plain_json_fields:
            val = data.get(field)
            if isinstance(val, str) and val:
                try:
                    data[field] = json.loads(val)
                except Exception:
                    pass  # leave as-is (plain string)

        # Look up maps from context
        user_map = self.context.get("user_map")
        socials_map = self.context.get("socials_map")
        mentor_profiles_map = self.context.get("mentor_profiles_map")
        mentor_socials_map = self.context.get("mentor_socials_map")

        # MUID fields — parse + enrich with user details
        for field in ["leads", "thinktank"]:
            val = data.get(field)
            if isinstance(val, str) and val:
                try:
                    parsed = json.loads(val)
                    data[field] = _resolve_muid_list(parsed, user_map=user_map, socials_map=socials_map)
                except Exception:
                    pass  # leave as-is if parsing fails

        # 'mentors' is served from UserIgLink (the authoritative IG-permission
        # table), not the legacy InterestGroup.mentors JSON column, so the IG
        # detail page always reflects actual mentor authority.
        from db.task import UserIgLink
        if hasattr(instance, "_prefetched_objects_cache") and "user_ig_link_ig" in instance._prefetched_objects_cache:
            mentor_links = [
                link for link in instance.user_ig_link_ig.all()
                if link.assignment_type == UserIgLink.AssignmentType.MENTOR and link.is_active
            ]
        else:
            mentor_links = None

        data["mentors"] = _resolve_ig_mentors(
            instance,
            mentor_links=mentor_links,
            mentor_socials_map=mentor_socials_map,
            mentor_profiles_map=mentor_profiles_map
        )

        return data


class InterestGroupCreateUpdateSerializer(serializers.ModelSerializer):
    # icon is no longer settable here — it's uploaded as a file via the
    # dedicated <pk>/icon-image/ endpoint, same as cover_image.

    class Meta:
        model = InterestGroup
        fields = [
            "name",
            "code",
            "category",
            "status",
            "about",
            "prerequisites",
            "career_opportunities",
            "resource",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
            "thinktank",
            "office_hours",
            "created_by",
            "updated_by",
        ]


class InterestGroupRequestSerializer(serializers.ModelSerializer):
    """Serializer for user-submitted IG creation requests."""
    # icon is no longer accepted here — it's uploaded as a file via the
    # dedicated <pk>/icon-image/ endpoint once the IG exists, same as
    # cover_image.

    class Meta:
        model = InterestGroup
        fields = [
            "name",
            "code",
            "category",
            "about",
            "prerequisites",
            "career_opportunities",
            "resource",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
            "thinktank",
            "office_hours",
        ]
        extra_kwargs = {
            "name": {"required": True},
            "code": {"required": True},
            "category": {"required": True},
        }

class InterestGroupRequestGetSerializer(InterestGroupSerializer):
    requester_muid = serializers.CharField(source="created_by.muid", read_only=True)
    requester_name = serializers.CharField(source="created_by.full_name", read_only=True)
    company_name = serializers.SerializerMethodField()

    class Meta(InterestGroupSerializer.Meta):
        fields = InterestGroupSerializer.Meta.fields + [
            "requester_muid",
            "requester_name",
            "company_name",
        ]

    def get_company_name(self, obj):
        from utils.types import RoleType, OrganizationType
        if obj.created_by:
            roles = obj.created_by.user_role_link_user.all().values_list("role__title", flat=True)
            if RoleType.COMPANY.value in roles:
                company_link = obj.created_by.user_organization_link_user.filter(
                    org__org_type=OrganizationType.COMPANY.value
                ).first()
                if company_link:
                    return company_link.org.title
        return None


def _strip_emails(entries):
    """Drop the 'email' key from each resolved muid/mentor dict.
    This endpoint is unauthenticated (public/ig/list/), so member emails
    (PII) must not be exposed — unlike the admin-only InterestGroupSerializer
    that reuses the same _resolve_muid_list/_resolve_ig_mentors helpers."""
    if not isinstance(entries, list):
        return entries
    for entry in entries:
        if isinstance(entry, dict):
            entry.pop("email", None)
    return entries


class PublicInterestGroupSerializer(serializers.ModelSerializer):
    impact_projects = ImpactProjectSerializer(source="impact_project_ig", many=True, read_only=True)

    class Meta:
        model = InterestGroup
        fields = [
            "id",
            "name",
            "leads",
            "mentors",
            "thinktank",
            "impact_projects",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Look up maps from context
        user_map = self.context.get("user_map")
        socials_map = self.context.get("socials_map")
        mentor_profiles_map = self.context.get("mentor_profiles_map")
        mentor_socials_map = self.context.get("mentor_socials_map")

        for field in ["leads", "thinktank"]:
            val = data.get(field)
            if isinstance(val, str) and val:
                try:
                    parsed = json.loads(val)
                    data[field] = _strip_emails(
                        _resolve_muid_list(parsed, user_map=user_map, socials_map=socials_map)
                    )
                except Exception:
                    pass

        from db.task import UserIgLink
        if hasattr(instance, "_prefetched_objects_cache") and "user_ig_link_ig" in instance._prefetched_objects_cache:
            mentor_links = [
                link for link in instance.user_ig_link_ig.all()
                if link.assignment_type == UserIgLink.AssignmentType.MENTOR and link.is_active
            ]
        else:
            mentor_links = None

        data["mentors"] = _strip_emails(_resolve_ig_mentors(
            instance,
            mentor_links=mentor_links,
            mentor_socials_map=mentor_socials_map,
            mentor_profiles_map=mentor_profiles_map
        ))

        return data

