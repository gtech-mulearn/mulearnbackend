with open(r"c:\Work\MULEARN\muLearn Backend\mulearnbackend\api\dashboard\campus\serializers.py", "a", encoding="utf-8") as f:
    f.write("""
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
""")
print("Serializer appended successfully")
