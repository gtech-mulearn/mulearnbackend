with open(r"c:\Work\MULEARN\muLearn Backend\mulearnbackend\api\dashboard\campus\campus_views.py", "a", encoding="utf-8") as f:
    f.write("""

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
""")
print("APIView appended successfully")
