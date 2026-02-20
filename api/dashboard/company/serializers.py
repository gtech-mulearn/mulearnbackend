from rest_framework import serializers

from db.company import Company


class CompanyReadSerializer(serializers.ModelSerializer):
    company_user_id = serializers.CharField(source='company_user.id', read_only=True)

    class Meta:
        model = Company
        fields = [
            'id', 'company_user_id', 'name', 'slug', 'logo',
            'description', 'industry_sector', 'website_link',
            'email', 'location', 'status', 'created_at', 'updated_at',
        ]


class CompanySelfUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'description', 'industry_sector', 'website_link',
            'email', 'location', 'logo',
        ]
        extra_kwargs = {
            'description': {'required': False},
            'industry_sector': {'required': False},
            'website_link': {'required': False},
            'email': {'required': False},
            'location': {'required': False},
            'logo': {'required': False},
        }

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class CompanyAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'name', 'description', 'industry_sector', 'website_link',
            'email', 'location', 'logo', 'status',
        ]
        extra_kwargs = {
            'name': {'required': False},
            'description': {'required': False},
            'industry_sector': {'required': False},
            'website_link': {'required': False},
            'email': {'required': False},
            'location': {'required': False},
            'logo': {'required': False},
            'status': {'required': False},
        }

    def validate_name(self, value):
        instance = self.instance
        if Company.objects.filter(name=value).exclude(id=instance.id).exists():
            raise serializers.ValidationError("Company with this name already exists.")
        return value

    def validate_status(self, value):
        valid = [c[0] for c in Company.STATUS_CHOICES]
        if value not in valid:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid)}"
            )
        return value

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by_id = user_id
        instance.save()
        return instance
