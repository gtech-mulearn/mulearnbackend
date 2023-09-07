from django.urls import path

from . import dynamic_role_view

urlpatterns = [ 
    path('', dynamic_role_view.DynamicRoleAPI.as_view()), #list
    path('create/', dynamic_role_view.DynamicRoleAPI.as_view()), #create
    path('delete/<str:type_id>/', dynamic_role_view.DynamicRoleAPI.as_view()), #delete
    path('update/<str:type_id>/', dynamic_role_view.DynamicRoleAPI.as_view()), #update
    path('types/', dynamic_role_view.DynamicTypeDropDownAPI.as_view()), #types
    path('roles/', dynamic_role_view.RoleDropDownAPI.as_view()), #roles
] 