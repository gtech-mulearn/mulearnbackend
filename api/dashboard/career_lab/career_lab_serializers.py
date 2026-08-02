from rest_framework import serializers

from db.career_lab import Hiring


class HiringSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.full_name')
    updated_by = serializers.ReadOnlyField(source='updated_by.full_name')

    class Meta:
        model = Hiring
        fields = [
            'id', 'posted_date', 'role', 'organization', 'title', 'location',
            'lastdate', 'applylink', 'jdlink', 'duration', 'remuneration',
            'vacancies', 'extracontent', 'created_by', 'created_at',
            'updated_by', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        return Hiring.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by_id = self.context.get('user_id')
        instance.save()
        return instance


class HiringCSVRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hiring
        fields = [
            'posted_date', 'role', 'organization', 'title', 'location',
            'lastdate', 'applylink', 'jdlink', 'duration', 'remuneration',
            'vacancies', 'extracontent',
        ]

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        return Hiring.objects.create(**validated_data)


class PublicOngoingHiringSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.full_name')
    updated_by = serializers.ReadOnlyField(source='updated_by.full_name')

    class Meta:
        model = Hiring
        fields = [
            'id', 'posted_date', 'role', 'organization', 'title', 'location',
            'lastdate', 'applylink', 'jdlink', 'duration', 'remuneration',
            'vacancies', 'created_by', 'created_at', 'updated_by', 'updated_at',
        ]


class PublicPreviousHiringSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.full_name')
    updated_by = serializers.ReadOnlyField(source='updated_by.full_name')

    class Meta:
        model = Hiring
        fields = [
            'id', 'role', 'organization', 'title', 'location', 'lastdate',
            'remuneration', 'vacancies', 'duration', 'extracontent',
            'created_by', 'created_at', 'updated_by', 'updated_at',
        ]
