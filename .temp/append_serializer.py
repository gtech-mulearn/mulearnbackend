with open(r"c:\Work\MULEARN\muLearn Backend\mulearnbackend\api\dashboard\campus\serializers.py", "a", encoding="utf-8") as f:
    f.write("""
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
""")
print("Serializer appended successfully")
