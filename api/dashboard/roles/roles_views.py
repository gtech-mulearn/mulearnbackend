from rest_framework.views import APIView

from utils.utils_views import CustomResponse


class HelloWorld(APIView):
    def get(self, request):
        return CustomResponse(response={'hey': "hello"}).get_success_response()

#TODO:
# all roles management or user role management?
# list existing roles
# create new role
# edit user role    
# delete user role
# get role of a specific user

#! items
# id
# title
# discord_id
# description
# updated_by
# updated_at
# no_of_people
# verified
# role_priority