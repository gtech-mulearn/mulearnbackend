import uuid

from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import serializers

from db.hackathon import Hackathon, HackathonForm, HackathonOrganiserLink
from db.organization import Organization, District
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils


class HackathonRetrivalSerializer(serializers.ModelSerializer):
    organisation = serializers.CharField(source='org.title')
    district = serializers.CharField(source='district.name')

    class Meta:
        model = Hackathon
        fields = fields = ('id',
                           'title', 'tagline', 'description', 'participant_count', 'organisation', 'district', 'place',
                           'is_open_to_all', 'application_start', 'application_ends', 'event_start', 'event_end',
                           'status',
                           'banner', 'event_logo', 'type')


class HackathonCreateUpdateDeleteSerializer(serializers.ModelSerializer):
    STATUS_CHOICES = (
        ("Draft", "Draft"),
        ("Completed", "Completed"),
        ("Published", "Published"),
        ("Deleted", "Deleted"),
    )
    title = serializers.CharField(
        error_messages={'required': 'Title field is required', 'blank': 'Title field may not be blank'})
    tagline = serializers.CharField(
        error_messages={'required': 'Tagline field is required', 'blank': 'tagline field may not be blank'})
    description = serializers.CharField(
        error_messages={'required': 'Description field is required', 'blank': 'description field may not be blank'})
    participant_count = serializers.IntegerField(
        error_messages={'required': 'ParticipantCount field is required',
                        'blank': 'participantCount field may not be blank'})
    org_id = serializers.CharField(
        error_messages={'required': 'orgId field is required', 'blank': 'orgId field may not be blank'})
    district_id = serializers.CharField(
        error_messages={'required': 'District field is required', 'blank': 'districtId field may not be blank'})
    place = serializers.CharField(
        error_messages={'required': 'Place field is required', 'blank': 'place field may not be blank'})

    is_open_to_all = serializers.BooleanField(
        error_messages={'required': 'Is Open To All field is required', 'blank': 'isOpenToAll field may not be blank'})
    application_start = serializers.DateTimeField(
        error_messages={'required': 'Application Start field is required',
                        'blank': 'applicationStart field may not be blank'})
    application_ends = serializers.DateTimeField(
        error_messages={'required': 'Application Ends field is required',
                        'blank': 'applicationEnds field may not be blank'})
    event_start = serializers.DateTimeField(
        error_messages={'required': 'Event Start field is required', 'blank': 'eventStart field may not be blank'})
    event_end = serializers.DateTimeField(
        error_messages={'required': 'Event Ends field is required', 'blank': 'eventEnd field may not be blank'})
    status = serializers.ChoiceField(choices=STATUS_CHOICES, error_messages={'required': 'Status  field is required'})
    form_fields = serializers.JSONField(required=True, error_messages={'required': 'Form Fields is required'})
    event_logo = serializers.ImageField(required=False)
    banner = serializers.ImageField(required=False)

    class Meta:
        model = Hackathon
        fields = (
            'title', 'tagline', 'description', 'participant_count', 'org_id', 'district_id', 'place',
            'is_open_to_all', 'application_start', 'application_ends', 'event_start', 'event_end', 'status',
            'form_fields',
            'event_logo', 'banner', 'event_logo')

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
            hackathon_form_fields = validated_data.pop('form_fields')
            user_id = JWTUtils.fetch_user_id(self.context.get('request'))
            validated_data['id'] = uuid.uuid4()
            validated_data['participant_count'] = validated_data.pop('participant_count')
            validated_data['org'] = validated_data.pop('org_id')
            validated_data['district'] = validated_data.pop('district_id')
            validated_data['is_open_to_all'] = validated_data.pop('is_open_to_all')
            validated_data['application_start'] = validated_data.pop('application_start')
            validated_data['application_ends'] = validated_data.pop('application_ends')
            validated_data['event_start'] = validated_data.pop('event_start')
            validated_data['event_end'] = validated_data.pop('event_end')
            validated_data['created_by_id'] = user_id
            validated_data['updated_by_id'] = user_id
            validated_data['created_at'] = DateTimeUtils.get_current_utc_time()
            validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()

            default_storage.save(validated_data.get('event_logo').name, validated_data.get('event_logo'))
            default_storage.save(validated_data.get('banner').name, validated_data.get('banner'))

            hackathon = Hackathon.objects.create(**validated_data)

            for field_name, field_type in hackathon_form_fields.items():
                HackathonForm.objects.create(id=uuid.uuid4(), hackathon=hackathon, field_name=field_name,
                                             field_type=field_type, updated_by_id=user_id,
                                             updated_at=DateTimeUtils.get_current_utc_time(), created_by_id=user_id,
                                             created_at=DateTimeUtils.get_current_utc_time(), )

            HackathonOrganiserLink.objects.create(id=uuid.uuid4(), organiser_id=user_id, hackathon=hackathon,
                                                  created_by_id=user_id, updated_by_id=user_id,
                                                  created_at=DateTimeUtils.get_current_utc_time(),
                                                  updated_at=DateTimeUtils.get_current_utc_time())

        return hackathon

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
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance

    def destroy(self, obj):
        obj.delete()
