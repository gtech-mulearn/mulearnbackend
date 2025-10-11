from django.urls import path

from . import dash_roles_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('user-role/<str:role_id>/', dash_roles_views.UserRoleSearchAPI.as_view(), name='search-user-role'),
    path('base-template/', dash_roles_views.RoleBaseTemplateAPI.as_view(), name="roles-base-template"),
    path('bulk-assign/', dash_roles_views.UserRoleLinkManagement.as_view(), name="user-roles-assign"), # used to assign a bunch of users a role
    path('bulk-assign/<str:role_id>/', dash_roles_views.UserRoleLinkManagement.as_view(), name="user-roles-list"), # used to get the list of users to assign a role
    path('bulk-assign-excel/', dash_roles_views.UserRoleBulkAssignAPI.as_view(), name="user-roles-assign-excel"), # used to bulk assign required roles to users from excel
    path('user-role/', dash_roles_views.UserRole.as_view(), name='create-delete-user-role'),
    path('', dash_roles_views.RoleAPI.as_view(), name="roles-list"),
    path('', dash_roles_views.RoleAPI.as_view(), name="roles-create"),
    path('csv/', dash_roles_views.RoleManagementCSV.as_view(), name="roles-csv"),
    path('<str:roles_id>/', dash_roles_views.RoleAPI.as_view(), name="roles-edit"),
    path('<str:roles_id>/', dash_roles_views.RoleAPI.as_view(), name="roles-delete"),

]
