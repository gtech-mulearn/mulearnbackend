from rest_framework import serializers
from db.task import Category


class CategoryListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.full_name", read_only=True)
    updated_by = serializers.CharField(source="updated_by.full_name", read_only=True)


    class Meta:
        model= Category
        fields= '__all__'

class CategoryCUDSerializer(serializers.ModelSerializer):
    class Meta:
        model= Category
        fields= '__all__'
        extra_kwargs = {
            'created_by': {'required': False},
            'updated_by': {'required': False},
        }

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        return Category.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        instance.updated_by_id = user_id
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance