"""
Serializers and validation for the Problem Statement system.
"""
import re
from urllib.parse import urlparse

from django.utils.text import slugify
from rest_framework import serializers

from db.problem_statement import (
    ProblemStatement,
    ProblemStatementInterest,
    ProblemStatementAuditLog,
)
from db.user import User
from db.company import Company

_URL_SCHEME_RE = re.compile(r'^https?://', re.IGNORECASE)


def _require_full_url(value, example):
    """Reject a URL link missing its http:// or https:// scheme or invalid type."""
    if not value:
        return value
    if not isinstance(value, str):
        raise serializers.ValidationError(
            f'Enter a full link starting with https:// (e.g. {example}).'
        )
    candidate = value.strip()
    if not _URL_SCHEME_RE.match(candidate) or not urlparse(candidate).netloc:
        raise serializers.ValidationError(
            f'Enter a full link starting with https:// (e.g. {example}).'
        )
    return value


class MinimalUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'muid', 'profile_pic']


class MinimalCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'logo', 'slug']


class ProblemStatementWriteSerializer(serializers.ModelSerializer):
    """Input serializer for POST /manage/ and PUT/PATCH /manage/<id>/."""

    class Meta:
        model = ProblemStatement
        fields = [
            'title', 'summary', 'description', 'cover_image',
            'categories', 'skills', 'requirements', 'expected_outcome', 'resources',
            'difficulty', 'reward_type', 'reward_details',
            'contact_email', 'external_link', 'deadline',
            'is_featured',
        ]
        extra_kwargs = {
            'title': {'required': True, 'allow_null': False, 'allow_blank': False},
            'summary': {'required': True, 'allow_null': False, 'allow_blank': False},
            'description': {'required': True, 'allow_null': False, 'allow_blank': False},
            'difficulty': {'required': False, 'allow_null': False, 'allow_blank': False},
            'reward_type': {'required': False, 'allow_null': False, 'allow_blank': False},
            'cover_image': {'required': False, 'allow_null': True},
            'categories': {'required': False, 'allow_null': True},
            'skills': {'required': False, 'allow_null': True},
            'requirements': {'required': False, 'allow_null': True},
            'expected_outcome': {'required': False, 'allow_null': True},
            'resources': {'required': False, 'allow_null': True},
            'reward_details': {'required': False, 'allow_null': True},
            'contact_email': {'required': False, 'allow_null': True},
            'external_link': {'required': False, 'allow_null': True},
            'deadline': {'required': False, 'allow_null': True},
            'is_featured': {'required': False},
        }

    def validate_title(self, value):
        if value is None or not str(value).strip():
            raise serializers.ValidationError('title cannot be null or empty.')
        return str(value).strip()

    def validate_summary(self, value):
        if value is None or not str(value).strip():
            raise serializers.ValidationError('summary cannot be null or empty.')
        return str(value).strip()

    def validate_description(self, value):
        if value is None or not str(value).strip():
            raise serializers.ValidationError('description cannot be null or empty.')
        return str(value).strip()

    def validate_external_link(self, value):
        if not value:
            return value
        return _require_full_url(value, 'https://example.com/problem-statement')

    def validate_contact_email(self, value):
        if not value:
            return value
        if not isinstance(value, str):
            raise serializers.ValidationError('Enter a valid email address.')
        email = value.strip()
        if '@' not in email or '.' not in email.split('@')[-1]:
            raise serializers.ValidationError('Enter a valid email address.')
        return email

    def validate_categories(self, value):
        if value is None:
            return value
        if not isinstance(value, list):
            raise serializers.ValidationError('categories must be a JSON array of strings/IDs.')
        if len(value) > 3:
            raise serializers.ValidationError('A maximum of 3 categories is allowed.')
        for item in value:
            if not isinstance(item, (str, int)):
                raise serializers.ValidationError('Each category item must be a string or integer ID.')
        return value

    def validate_skills(self, value):
        if value is None:
            return value
        if not isinstance(value, list):
            raise serializers.ValidationError('skills must be a JSON array of strings/IDs.')
        if len(value) > 15:
            raise serializers.ValidationError('A maximum of 15 skills is allowed.')
        for item in value:
            if not isinstance(item, (str, int)):
                raise serializers.ValidationError('Each skill item must be a string or integer ID.')
        return value

    def validate_resources(self, value):
        if value is None:
            return value
        if not isinstance(value, list):
            raise serializers.ValidationError('resources must be a JSON array.')
        if len(value) > 10:
            raise serializers.ValidationError('A maximum of 10 resource items is allowed.')
        for item in value:
            if isinstance(item, str):
                _require_full_url(item, 'https://example.com/resource')
            elif isinstance(item, dict):
                if 'link' in item and item['link'] is not None:
                    link_val = item['link']
                    if not isinstance(link_val, str):
                        raise serializers.ValidationError('Resource link must be a valid URL string.')
                    _require_full_url(link_val, 'https://example.com/resource')
                else:
                    raise serializers.ValidationError('Resource object must contain a non-empty "link" string field.')
            else:
                raise serializers.ValidationError('Resource item must be a string URL or object with a "link" field.')
        return value

    def _generate_unique_slug(self, title):
        base = slugify(title)
        slug = base
        counter = 1
        while ProblemStatement.objects.filter(slug=slug).exists():
            slug = f'{base}-{counter}'
            counter += 1
        return slug


class ProblemStatementListItemSerializer(serializers.ModelSerializer):
    """Output serializer for paginated list endpoints (public & learner feeds)."""
    company = MinimalCompanySerializer(read_only=True)
    viewer_interested = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = ProblemStatement
        fields = [
            'id', 'company', 'title', 'slug', 'summary', 'cover_image',
            'categories', 'skills', 'difficulty', 'reward_type',
            'deadline', 'status', 'is_featured', 'view_count',
            'interest_count', 'viewer_interested', 'created_at',
        ]


class ProblemStatementDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer for problem statements."""
    company = MinimalCompanySerializer(read_only=True)
    created_by = MinimalUserSerializer(read_only=True)
    updated_by = MinimalUserSerializer(read_only=True)
    viewer_interested = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = ProblemStatement
        fields = [
            'id', 'company', 'title', 'slug', 'summary', 'description',
            'categories', 'skills', 'requirements', 'expected_outcome',
            'resources', 'cover_image', 'difficulty', 'reward_type',
            'reward_details', 'contact_email', 'external_link', 'deadline',
            'status', 'removal_reason', 'is_featured', 'view_count',
            'interest_count', 'viewer_interested', 'published_at',
            'closed_at', 'archived_at', 'created_by', 'updated_by',
            'created_at', 'updated_at',
        ]


class ProblemStatementInterestSerializer(serializers.ModelSerializer):
    """Serializer for learner interest expression and work link submission."""

    class Meta:
        model = ProblemStatementInterest
        fields = ['note', 'work_link', 'status']
        read_only_fields = ['status']
        extra_kwargs = {
            'note': {'required': False, 'allow_null': True},
            'work_link': {'required': False, 'allow_null': True},
        }

    def validate_work_link(self, value):
        if not value:
            return value
        return _require_full_url(value, 'https://github.com/username/project')


class ProblemStatementAuditLogSerializer(serializers.ModelSerializer):
    """Output serializer for embedded audit history in management views."""
    actor = MinimalUserSerializer(read_only=True)

    class Meta:
        model = ProblemStatementAuditLog
        fields = [
            'id', 'target_type', 'target_id', 'action',
            'actor', 'actor_role', 'metadata', 'created_at',
        ]
