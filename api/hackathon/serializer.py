import json
import uuid

from django.conf import settings
from django.db import transaction
from rest_framework import serializers

from db.hackathon import Hackathon, HackathonForm, HackathonOrganiserLink, HackathonUserSubmission
from db.organization import Organization, District, UserOrganizationLink
from db.user import User
from utils.permission import JWTUtils
from utils.types import OrganizationType
from utils.utils import DateTimeUtils


class HackathonRetrivalSerializer(serializers.ModelSerializer):
    organisation = serializers.CharField(source='org.title', allow_null=True)
    district = serializers.CharField(source='district.name', allow_null=True)
    org_id = serializers.CharField(source='org.id', allow_null=True)
    district_id = serializers.CharField(source='district.id', allow_null=True)
    editable = serializers.SerializerMethodField()

    banner = serializers.SerializerMethodField()
    event_logo = serializers.SerializerMethodField()

    class Meta:
        model = Hackathon
        fields = ('id',
                  'title', 'tagline', 'description', 'participant_count', 'organisation', 'district', 'place',
                  'is_open_to_all', 'application_start', 'application_ends', 'event_start', 'event_end',
                  'status',
                  'banner', 'event_logo', 'type', 'website', 'editable', 'org_id', 'district_id')

    def get_banner(self, obj):
        media = obj.banner
        if media:
            return f"{settings.MEDIA_URL}{media}"
        return None

    def get_event_logo(self, obj):
        media = obj.event_logo
        if media:
            return f"{settings.MEDIA_URL}{media}"
        return None

    def get_editable(self, obj):
        user_id = self.context.get('user_id')
        return HackathonOrganiserLink.objects.filter(organiser=user_id, hackathon=obj).exists()


class UpcomingHackathonRetrivalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hackathon
        fields = ('id', 'title', 'description', 'event_logo', 'banner')


class HackathonCreateUpdateDeleteSerializer(serializers.ModelSerializer):
    STATUS_CHOICES = (
        ("Draft", "Draft"),
        ("Completed", "Completed"),
        ("Published", "Published"),
        ("Deleted", "Deleted"),
    )
    TYPE_CHOICES = (
        ("offline", "offline"),
        ("online", "online"),
    )
    title = serializers.CharField(required=True)
    status = serializers.ChoiceField(choices=STATUS_CHOICES, required=False)
    form_fields = serializers.JSONField(required=False)
    event_logo = serializers.ImageField(required=False, allow_null=True)
    banner = serializers.ImageField(required=False, allow_null=True)
    org_id = serializers.CharField(required=False)
    district_id = serializers.CharField(required=False)
    website = serializers.CharField(required=False, allow_null=True)
    type = serializers.ChoiceField(choices=TYPE_CHOICES, required=False)

    class Meta:
        model = Hackathon
        fields = (
            'title', 'tagline', 'description', 'participant_count', 'org_id', 'district_id', 'place',
            'is_open_to_all', 'application_start', 'application_ends', 'event_start', 'event_end', 'status',
            'form_fields', 'type',
            'event_logo', 'banner', 'event_logo', 'website')

    def validate_org_id(self, value):
        organisation = Organization.objects.filter(id=value).first()
        if not organisation:
            raise serializers.ValidationError('Organisation Not Exists')
        return organisation

    def validate_district_id(self, value):
        district = District.objects.filter(id=value).first()
        if not district:
            raise serializers.ValidationError("District Not Exists")
        return district

    def create(self, validated_data):

        with transaction.atomic():
            hackathon_form_fields = None
            if 'form_fields' in validated_data:
                hackathon_form_fields = validated_data.pop('form_fields')

            user_id = JWTUtils.fetch_user_id(self.context.get('request'))
            validated_data['id'] = uuid.uuid4()
            validated_data['created_by_id'] = user_id
            validated_data['updated_by_id'] = user_id
            validated_data['created_at'] = DateTimeUtils.get_current_utc_time()
            validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()

            validated_data['org'] = validated_data.pop('org_id') if validated_data.get('org_id', None) else None
            validated_data['district'] = validated_data.pop('district_id') if validated_data.get('district_id',
                                                                                                 None) else None

            hackathon = Hackathon.objects.create(**validated_data)

            if hackathon_form_fields:
                for field_name, field_type in hackathon_form_fields.items():
                    HackathonForm.objects.create(id=uuid.uuid4(), hackathon=hackathon, field_name=field_name,
                                                 field_type=field_type, updated_by_id=user_id,
                                                 updated_at=DateTimeUtils.get_current_utc_time(), created_by_id=user_id,
                                                 created_at=DateTimeUtils.get_current_utc_time())

            HackathonOrganiserLink.objects.create(id=uuid.uuid4(), organiser_id=user_id, hackathon=hackathon,
                                                  created_by_id=user_id, updated_by_id=user_id,
                                                  created_at=DateTimeUtils.get_current_utc_time(),
                                                  updated_at=DateTimeUtils.get_current_utc_time())

        return hackathon

    def destroy(self, obj):
        obj.delete()


class HackathonUpdateSerializer(serializers.ModelSerializer):
    STATUS_CHOICES = (
        ("Draft", "Draft"),
        ("Completed", "Completed"),
        ("Deleted", "Deleted"),
    )
    TYPE_CHOICES = (
        ("offline", "offline"),
        ("online", "online"),
    )
    title = serializers.CharField(required=False)
    status = serializers.ChoiceField(choices=STATUS_CHOICES, required=False)
    form_fields = serializers.JSONField(required=False)
    event_logo = serializers.ImageField(required=False, allow_null=True)
    banner = serializers.ImageField(required=False, allow_null=True)
    org_id = serializers.CharField(required=False)
    district_id = serializers.CharField(required=False)
    website = serializers.CharField(required=False, allow_null=True)
    type = serializers.ChoiceField(choices=TYPE_CHOICES, required=False)

    class Meta:
        model = Hackathon
        fields = ('title', 'tagline', 'description', 'participant_count', 'org_id', 'district_id', 'place',
                  'is_open_to_all', 'application_start', 'application_ends', 'event_start', 'event_end', 'status',
                  'form_fields', 'type',
                  'event_logo', 'banner', 'event_logo', 'website')

    def validate_org_id(self, value):
        organisation = Organization.objects.filter(id=value).first()
        if not organisation:
            raise serializers.ValidationError('Organisation Not Exists')
        return organisation

    def validate_district_id(self, value):
        district = District.objects.filter(id=value).first()
        if not district:
            raise serializers.ValidationError("District Not Exists")
        return district

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        instance.title = validated_data.get('title', instance.title)
        instance.tagline = validated_data.get('tagline', instance.tagline)
        instance.description = validated_data.get('description', instance.description)
        instance.participant_count = validated_data.get('participant_count', instance.participant_count)
        instance.org = validated_data.get('org_id', instance.org)
        instance.district = validated_data.get('district_id', instance.district)
        instance.place = validated_data.get('place', instance.place)
        instance.is_open_to_all = validated_data.get('is_open_to_all', instance.is_open_to_all)
        instance.application_start = validated_data.get('application_start', instance.application_start)
        instance.application_ends = validated_data.get('application_ends', instance.application_ends)
        instance.event_start = validated_data.get('event_start', instance.event_start)
        instance.event_end = validated_data.get('event_end', instance.event_end)
        instance.status = validated_data.get('status', instance.status)
        instance.website = validated_data.get('website', instance.website)
        instance.type = validated_data.get('type', instance.type)
        instance.event_logo = validated_data.get('event_logo', instance.event_logo)
        instance.banner = validated_data.get('banner', instance.banner)
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()

        if 'form_fields' in validated_data:
            hackathon_form_fields = validated_data.pop('form_fields')
            if hackathon_form_fields:
                for field_name, field_type in hackathon_form_fields.items():
                    hackathon = HackathonForm.objects.filter(field_name=field_name, hackathon=instance).first()
                    if not hackathon:
                        HackathonForm.objects.create(id=uuid.uuid4(), hackathon=instance, field_name=field_name,
                                                     field_type=field_type, updated_by_id=user_id,
                                                     updated_at=DateTimeUtils.get_current_utc_time(),
                                                     created_by_id=user_id,
                                                     created_at=DateTimeUtils.get_current_utc_time())
        instance.save()
        return instance


class HackathonPublishingSerializer(serializers.ModelSerializer):
    STATUS_CHOICES = (
        ("Published", "Published"),
        ("Draft", "Draft"),
    )

    status = serializers.ChoiceField(choices=STATUS_CHOICES, required=True)

    class Meta:
        model = Hackathon
        fields = ('status',)

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        instance.status = validated_data.get('status', instance.status)
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()

        instance.save()
        return instance


class HackathonUserSubmissionSerializer(serializers.ModelSerializer):
    hackathon_id = serializers.CharField(required=False)
    data = serializers.JSONField(required=False)

    class Meta:
        model = HackathonUserSubmission
        fields = ('hackathon_id', 'data')

    def validate_hackathon_id(self, value):
        hackathon = Hackathon.objects.filter(id=value).first()
        if not hackathon:
            raise serializers.ValidationError("Hackathon Not Exists")
        existing_submission = HackathonUserSubmission.objects.filter(hackathon_id=value,
                                                                     user_id=self.context.get('user_id')).first()
        if existing_submission:
            raise serializers.ValidationError("User has already submitted for this hackathon.")
        return hackathon.id

    def create(self, validated_data):
        with transaction.atomic():
            user_id = JWTUtils.fetch_user_id(self.context.get('request'))
            validated_data['id'] = uuid.uuid4()
            validated_data['user_id'] = user_id
            validated_data['created_by_id'] = user_id
            validated_data['updated_by_id'] = user_id
            validated_data['created_at'] = DateTimeUtils.get_current_utc_time()
            validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()

            hackathon_submission = HackathonUserSubmission.objects.create(**validated_data)
        return hackathon_submission


class HackathonOrganiserSerializer(serializers.ModelSerializer):
    mu_id = serializers.CharField(required=False)

    class Meta:
        model = HackathonOrganiserLink
        fields = ('mu_id',)

    def validate_mu_id(self, value):
        user = User.objects.filter(mu_id=value).first()
        if not user:
            raise serializers.ValidationError("User Not Exists")

        if user:
            if HackathonOrganiserLink.objects.filter(organiser=user,
                                                     hackathon__id=self.context.get('hackathon').id).exists():
                raise serializers.ValidationError("This User Already An Organizer in this hackathon")

        return user.id

    def create(self, validated_data):
        with transaction.atomic():
            organizer_id = validated_data.pop('mu_id')
            user_id = JWTUtils.fetch_user_id(self.context.get('request'))
            validated_data['id'] = uuid.uuid4()
            validated_data['hackathon_id'] = self.context.get('hackathon').id
            validated_data['organiser_id'] = organizer_id
            validated_data['created_by_id'] = user_id
            validated_data['updated_by_id'] = user_id
            validated_data['created_at'] = DateTimeUtils.get_current_utc_time()
            validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
            organiser = HackathonOrganiserLink.objects.create(**validated_data)
        return organiser

    def destroy(self, obj):
        obj.delete()


class ListApplicantsSerializer(serializers.ModelSerializer):
    data = serializers.SerializerMethodField()

    class Meta:
        model = HackathonUserSubmission
        fields = ('data',)

    def get_data(self, obj):
        try:
            return json.loads(obj.data.replace("'", "\""))
        except json.JSONDecodeError:
            return {}


class HackathonInfoSerializer(serializers.ModelSerializer):
    banner = serializers.SerializerMethodField()
    event_logo = serializers.SerializerMethodField()
    organisation = serializers.CharField(source='org.title', allow_null=True)
    district = serializers.CharField(source='district.name', allow_null=True)
    org_id = serializers.CharField(source='org.id', allow_null=True)
    district_id = serializers.CharField(source='district.id', allow_null=True)
    user_info = serializers.SerializerMethodField()

    class Meta:
        model = Hackathon
        fields = ('id',
                  'title', 'tagline', 'description', 'participant_count', 'organisation', 'district', 'place',
                  'is_open_to_all', 'application_start', 'application_ends', 'event_start', 'event_end',
                  'status',
                  'banner', 'event_logo', 'type', 'website', 'org_id', 'district_id'
                                                                       'user_info'

                  )

    def get_banner(self, obj):
        media = obj.banner
        if media:
            return f"{settings.MEDIA_URL}{media}"
        return None

    def get_event_logo(self, obj):
        media = obj.event_logo
        if media:
            return f"{settings.MEDIA_URL}{media}"
        return None

    def get_user_info(self, obj):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        user = User.objects.filter(id=user_id).first()
        user_org_link = UserOrganizationLink.objects.filter(user=user,
                                                            org__org_type=OrganizationType.COLLEGE.value).first()
        return {'name': user.fullname, 'gender': user.gender, 'email': user.email, 'mobile': user.mobile,
                'college': user_org_link.org.title}


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('id', 'title')


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ('id', 'name')


class HackathonFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = HackathonForm
        fields = ('field_name', 'field_type', 'is_required')


class HackathonOrganiserSerializerRetrival(serializers.ModelSerializer):
    full_name = serializers.CharField(source='organiser.fullname')
    email = serializers.CharField(source='organiser.email')
    muid = serializers.CharField(source='organiser.mu_id')
    profile_pic = serializers.CharField(source='organiser.profile_pic')

    class Meta:
        model = HackathonOrganiserLink
        fields = ('id', 'full_name', 'email', 'muid', 'profile_pic')
