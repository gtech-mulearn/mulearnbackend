from django.db.models import Count
from rest_framework.views import APIView

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternGuildStatus
from utils.utils import CommonUtils
from db.intern import UserInternGuildLink

from .serializers import ManageInternSerializer

class ManageInternAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, intern_id=None):
        if intern_id:
            intern = UserInternGuildLink.objects.filter(id=intern_id).first()
            if not intern:
                return CustomResponse(general_message="Intern not found.").get_failure_response()
            serializer = ManageInternSerializer(intern)
            return CustomResponse(response=serializer.data).get_success_response()
            
        interns = UserInternGuildLink.objects.all().order_by('-created_at')
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            interns, request,
            ['user__fullname', 'guild', 'status'],
            {'created_at': 'created_at', 'status': 'status'}
        )
        
        serializer = ManageInternSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = ManageInternSerializer(data=request.data, context={'user_id': user_id})
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message="Intern onboarded successfully.").get_success_response()
            
        return CustomResponse(response=serializer.errors).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, intern_id):
        user_id = JWTUtils.fetch_user_id(request)
        intern = UserInternGuildLink.objects.filter(id=intern_id).first()
        if not intern:
            return CustomResponse(general_message="Intern not found.").get_failure_response()
            
        old_data = {
            "guild": intern.guild,
            "status": intern.status
        }
            
        serializer = ManageInternSerializer(intern, data=request.data, partial=True, context={'user_id': user_id})
        
        if serializer.is_valid():
            serializer.save()
            
            new_guild = request.data.get("guild")
            if new_guild and new_guild != old_data["guild"]:
                from db.mentor import SystemActionLog
                SystemActionLog.objects.create(
                    action_type=SystemActionLog.ActionType.INTERN_GUILD_REASSIGN.value,
                    actor_user_id=user_id,
                    subject_user_id=intern.user_id,
                    entity_name='user_intern_guild_link',
                    entity_id=intern.id,
                    old_data=old_data,
                    new_data={"guild": new_guild, "status": intern.status}
                )
            
            return CustomResponse(general_message="Intern details updated successfully.").get_success_response()
            
        return CustomResponse(response=serializer.errors).get_failure_response()

class ManageInternStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        stats = UserInternGuildLink.objects.values('status').annotate(count=Count('id'))
        
        data = {
            InternGuildStatus.ACTIVE.value: 0,
            InternGuildStatus.AT_RISK.value: 0,
            InternGuildStatus.ON_LEAVE.value: 0,
            InternGuildStatus.INACTIVE.value: 0,
        }
        
        for stat in stats:
            data[stat['status']] = stat['count']
            
        return CustomResponse(response=data).get_success_response()

class ManageInternExportAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        interns = UserInternGuildLink.objects.all().select_related('user')
        
        # We can reuse the CommonUtils method to generate a CSV response if it exists,
        # but otherwise we can manually build it or use a library.
        # We'll just build a basic CSV string and return it in CustomResponse or as HttpResponse.
        from django.http import HttpResponse
        import csv
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="interns.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Full Name', 'MuID', 'Guild', 'Status', 'Created At'])
        
        for intern in interns:
            writer.writerow([
                intern.user.fullname,
                intern.user.muid,
                intern.guild,
                intern.status,
                intern.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
            
        return response
