import jwt
from decouple import config
from rest_framework.permissions import BasePermission
from django.utils import timezone
from datetime import datetime
from db.launchpad import LaunchpadCompanies, LaunchpadRecruiters
from utils.response import CustomResponse

class LaunchpadJWTPermission(BasePermission):
    
    def has_permission(self, request, view):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(
                token,
                config("SECRET_KEY"),
                algorithms=["HS256"],
                verify=True,
            )
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False
        
        user_id = payload.get("id")
        user_type = payload.get("user_type")
        token_type = payload.get("tokenType")
        
        if token_type != "access":
            return False
        
        # Get user based on type
        user = None
        if user_type == "company":
            try:
                user = LaunchpadCompanies.objects.get(id=user_id)
            except LaunchpadCompanies.DoesNotExist:
                return False
        elif user_type == "recruiter":
            try:
                user = LaunchpadRecruiters.objects.get(id=user_id)
            except LaunchpadRecruiters.DoesNotExist:
                return False
        else:
            return False
        
        request.launchpad_user = user
        request.launchpad_user_type = user_type
        
        return True