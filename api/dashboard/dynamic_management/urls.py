from django.urls import path

from . import dynamic_management_view

urlpatterns = [ 
    path('dynamic-role/', dynamic_management_view.DynamicRoleAPI.as_view()), #list
    path('dynamic-role/create/', dynamic_management_view.DynamicRoleAPI.as_view()), #create
    path('dynamic-role/delete/<str:type_id>/', dynamic_management_view.DynamicRoleAPI.as_view()), #delete
    path('dynamic-role/update/<str:type_id>/', dynamic_management_view.DynamicRoleAPI.as_view()), #update
    path('dynamic-role/types/', dynamic_management_view.DynamicTypeDropDownAPI.as_view()), #types
    path('dynamic-role/roles/', dynamic_management_view.RoleDropDownAPI.as_view()), #roles
] 