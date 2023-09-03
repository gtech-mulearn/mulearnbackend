from django.urls import path

from . import dynamic_role_view

urlpatterns = [ 
    path('', dynamic_role_view.DynamicRoleAPI.as_view()), #list
    path('create/', dynamic_role_view.DynamicRoleAPI.as_view()), #create
    path('delete/', dynamic_role_view.DynamicRoleAPI.as_view()), #delete
    path('update/', dynamic_role_view.DynamicRoleAPI.as_view()), #update
] 