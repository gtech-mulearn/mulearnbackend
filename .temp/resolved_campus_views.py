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
        
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get('pagination')
        )


class CampusShowcaseAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        org_id = user_org_link.org_id
        try:
            from db.organization import CollegeShowcase
            showcase = CollegeShowcase.objects.get(org_id=org_id)
            serializer = serializers.CampusShowcaseSerializer(showcase)
            return CustomResponse(response=serializer.data).get_success_response()
        except CollegeShowcase.DoesNotExist:
            return CustomResponse(
                general_message="Showcase not found for this campus"
            ).get_failure_response()

    @role_required([RoleType.CAMPUS_LEAD.value, RoleType.LEAD_ENABLER.value])
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        if not (user_org_link := get_user_college_link(user_id)):
            return CustomResponse(
                general_message="User have no organization"
            ).get_failure_response()

        org_id = user_org_link.org_id
        try:
            from db.organization import CollegeShowcase
            showcase = CollegeShowcase.objects.get(org_id=org_id)
            serializer = serializers.CampusShowcaseSerializer(showcase, data=request.data, partial=True, context={'user_id': user_id, 'org_id': org_id})
        except CollegeShowcase.DoesNotExist:
            serializer = serializers.CampusShowcaseSerializer(data=request.data, context={'user_id': user_id, 'org_id': org_id})

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Campus showcase updated successfully"
            ).get_success_response()
            
        return CustomResponse(
            response=serializer.errors
        ).get_failure_response()
