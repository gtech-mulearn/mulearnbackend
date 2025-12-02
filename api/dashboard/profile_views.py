from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from db.user import User

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "bio": user.bio,
            "projects": user.projects,
            "experience": user.experience
        })

    def patch(self, request):
        user = request.user
        data = request.data
        
        if 'bio' in data:
            user.bio = data['bio']
        if 'projects' in data:
            user.projects = data['projects']
        if 'experience' in data:
            user.experience = data['experience']
            
        user.save()
        return Response({"message": "Profile updated successfully"})