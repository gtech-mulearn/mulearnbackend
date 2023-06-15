import uuid

from django.db import transaction
from rest_framework import serializers

from db.hackathon import Hackathon, HackathonForm, HackathonOrganiserLink
from db.organization import Organization, District
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils


class HackathonRetrivalSerailzier(serializers.ModelSerializer):
    participantCount = serializers.IntegerField(source='participant_count')
    organisation = serializers.CharField(source='org.title')
    district = serializers.CharField(source='district.name')
    isOpenToAll = serializers.BooleanField(source='is_open_to_all')
    applicationStart = serializers.DateTimeField(source='application_start')
    applicationEnds = serializers.CharField(source='application_ends')
    eventStart = serializers.CharField(source='event_start')
    eventEnd = serializers.CharField(source='event_end')

    class Meta:
        model = Hackathon
        fields = fields = ('id',
                           'title', 'tagline', 'description', 'participantCount', 'organisation', 'district', 'place',
                           'isOpenToAll', 'applicationStart', 'applicationEnds', 'eventStart', 'eventEnd', 'status')


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
    participantCount = serializers.IntegerField(
        error_messages={'required': 'ParticipantCount field is required',
                        'blank': 'participantCount field may not be blank'})
    orgId = serializers.CharField(
        error_messages={'required': 'orgId field is required', 'blank': 'orgId field may not be blank'})
    districtId = serializers.CharField(
        error_messages={'required': 'District field is required', 'blank': 'districtId field may not be blank'})
    place = serializers.CharField(
        error_messages={'required': 'Place field is required', 'blank': 'place field may not be blank'})
    # eventLogo = serializers.CharField(
    #     error_messages={'required': 'event logo field is required', 'blank': 'eventLogo field may not be blank'})
    # banner = serializers.CharField(
    #     error_messages={'required': 'Banner field is required', 'blank': 'banner field may not be blank'})
    isOpenToAll = serializers.BooleanField(
        error_messages={'required': 'Is Open To All field is required', 'blank': 'isOpenToAll field may not be blank'})
    applicationStart = serializers.DateTimeField(
        error_messages={'required': 'Application Start field is required',
                        'blank': 'applicationStart field may not be blank'})
    applicationEnds = serializers.DateTimeField(
        error_messages={'required': 'Application Ends field is required',
                        'blank': 'applicationEnds field may not be blank'})
    eventStart = serializers.DateTimeField(
        error_messages={'required': 'Event Start field is required', 'blank': 'eventStart field may not be blank'})
    eventEnd = serializers.DateTimeField(
        error_messages={'required': 'Event Ends field is required', 'blank': 'eventEnd field may not be blank'})
    status = serializers.ChoiceField(choices=STATUS_CHOICES, error_messages={'required': 'Status  field is required'})
    formFields = serializers.JSONField(required=True, error_messages={'required': 'Form Fields is required'})

    class Meta:
        model = Hackathon
        fields = (
            'title', 'tagline', 'description', 'participantCount', 'orgId', 'districtId', 'place',
            'isOpenToAll', 'applicationStart', 'applicationEnds', 'eventStart', 'eventEnd', 'status', 'formFields')

    def validate_orgId(self, value):
        organisation = Organization.objects.filter(id=value).first()
        if not organisation:
            raise serializers.ValidationError('Organisation Not Exists')
        return organisation

    def validate_districtId(self, value):
        district = District.objects.filter(id=value).first()
        if not district:
            raise serializers.ValidationError("District Not Exists")
        return district

    def create(self, validated_data):
        with transaction.atomic():
            hackathon_form_fields = validated_data.pop('formFields')
            user_id = JWTUtils.fetch_user_id(self.context.get('request'))
            validated_data['id'] = uuid.uuid4()
            validated_data['participant_count'] = validated_data.pop('participantCount')
            validated_data['org'] = validated_data.pop('orgId')
            validated_data['district'] = validated_data.pop('districtId')
            validated_data['is_open_to_all'] = validated_data.pop('isOpenToAll')
            validated_data['application_start'] = validated_data.pop('applicationStart')
            validated_data['application_ends'] = validated_data.pop('applicationEnds')
            validated_data['event_start'] = validated_data.pop('eventStart')
            validated_data['event_end'] = validated_data.pop('eventEnd')
            validated_data['created_by_id'] = user_id
            validated_data['updated_by_id'] = user_id
            validated_data['created_at'] = DateTimeUtils.get_current_utc_time()
            validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
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
        instance.participant_count = validated_data.get('participantCount', instance.participant_count)
        instance.org = validated_data.get('orgId', instance.org)
        instance.district = validated_data.get('districtId', instance.district)
        instance.place = validated_data.get('place', instance.place)
        instance.is_open_to_all = validated_data.get('isOpenToAll', instance.is_open_to_all)
        instance.application_start = validated_data.get('applicationStart', instance.application_start)
        instance.application_ends = validated_data.get('applicationEnds', instance.application_ends)
        instance.event_start = validated_data.get('eventStart', instance.event_start)
        instance.event_end = validated_data.get('eventEnd', instance.event_end)
        instance.status = validated_data.get('status', instance.status)
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance

    def destroy(self, obj):
        obj.delete()
