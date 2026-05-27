with open(r"c:\Work\MULEARN\muLearn Backend\mulearnbackend\api\dashboard\campus\campus_views.py", "a", encoding="utf-8") as f:
    f.write("""

class CampusStudentActivityAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request, muid):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(general_message="User have no organization").get_failure_response()

        org_id = user_org_link.org_id
        
        # Verify if the student (muid) belongs to this campus
        try:
            student = User.objects.get(muid=muid)
            is_student_in_campus = UserOrganizationLink.objects.filter(
                user=student, org_id=org_id
            ).exists()
            if not is_student_in_campus:
                return CustomResponse(general_message="Student not found in this campus").get_failure_response()
        except User.DoesNotExist:
            return CustomResponse(general_message="Student not found").get_failure_response()

        from db.task import KarmaActivityLog
        activity_logs = KarmaActivityLog.objects.filter(
            user=student
        ).select_related('task', 'task__ig').order_by('-created_at')

        paginated_queryset = CommonUtils.get_paginated_queryset(activity_logs, request, ["task__title", "task__ig__name"])
        serializer = serializers.StudentActivityTimelineSerializer(paginated_queryset.get('queryset'), many=True)
        
        return CustomResponse(
            response=serializer.data,
            pagination=paginated_queryset.get('pagination')
        ).get_success_response()
""")
print("View appended successfully")
