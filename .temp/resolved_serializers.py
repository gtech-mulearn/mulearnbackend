class StudentActivityTimelineSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source="task.title", read_only=True)
    ig_name = serializers.CharField(source="task.ig.name", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = KarmaActivityLog
        fields = ["id", "task_name", "ig_name", "karma", "status", "created_at"]

    def get_status(self, obj):
        if obj.appraiser_approved:
            return "Approved"
        elif obj.appraiser_approved is False:
            return "Rejected"
        return "Pending"


class CampusShowcaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollegeShowcase
        fields = [
            "org_id",
            "about",
            "hero_image",
            "highlights",
            "gallery",
            "testimonials",
            "contact_email",
            "contact_phone",
            "updated_at"
        ]
        read_only_fields = ["org_id", "updated_at"]

    def create(self, validated_data):
        org_id = self.context.get("org_id")
        user_id = self.context.get("user_id")

        showcase, created = CollegeShowcase.objects.update_or_create(
            org_id=org_id,
            defaults={
                **validated_data,
                "updated_by_id": user_id,
                "created_by_id": user_id if not getattr(self, 'instance', None) else self.instance.created_by_id
            }
        )
        return showcase

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        if user_id:
            instance.updated_by_id = user_id
        return super().update(instance, validated_data)
