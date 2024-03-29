from django.urls import path

from . import dynamic_management_view

urlpatterns = [ 
    path('dynamic-role/', dynamic_management_view.DynamicRoleAPI.as_view()), #list
    path('dynamic-role/create/', dynamic_management_view.DynamicRoleAPI.as_view()), #create
    path('dynamic-role/delete/<str:type_id>/', dynamic_management_view.DynamicRoleAPI.as_view()), #delete
    path('dynamic-role/update/<str:type_id>/', dynamic_management_view.DynamicRoleAPI.as_view()), #update

    path('dynamic-user/', dynamic_management_view.DynamicUserAPI.as_view()), #list
    path('dynamic-user/create/', dynamic_management_view.DynamicUserAPI.as_view()), #create
    path('dynamic-user/delete/<str:type_id>/', dynamic_management_view.DynamicUserAPI.as_view()), #delete
    path('dynamic-user/update/<str:type_id>/', dynamic_management_view.DynamicUserAPI.as_view()), #update

    path('types/', dynamic_management_view.DynamicTypeDropDownAPI.as_view()), #types
    path('roles/', dynamic_management_view.RoleDropDownAPI.as_view()), #roles
] 