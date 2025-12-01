from rest_framework.views import APIView
from rest_framework.response import Response
from db.organization import CampusExecom, Organization
from db.user import User
import uuid

class CampusExecomView(APIView):
    
    # 1. VIEW EXECOM MEMBERS (GET)
    def get(self, request, campus_id):
        members = CampusExecom.objects.filter(campus_id=campus_id).values(
            'id', 'user__first_name', 'user__last_name', 'role', 'user__email'
        )
        return Response({'data': list(members)})

    # 2. ADD MEMBER (POST)
    def post(self, request, campus_id):
        user_id = request.data.get('user_id')
        role = request.data.get('role')

        if not user_id or not role:
            return Response({'message': 'User ID and Role are required'}, status=400)

        if CampusExecom.objects.filter(campus_id=campus_id, user_id=user_id).exists():
             return Response({'message': 'User is already in Execom'}, status=400)

        CampusExecom.objects.create(
            id=str(uuid.uuid4()),
            user_id=user_id,
            campus_id=campus_id,
            role=role
        )
        return Response({'message': 'Member added successfully'})

    # 3. REMOVE MEMBER (DELETE)
    def delete(self, request, campus_id, uid):
        CampusExecom.objects.filter(id=uid).delete()
        return Response({'message': 'Member removed successfully'})