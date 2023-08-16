from django.urls import path

from . import dash_roles_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('search-role/', dash_roles_views.UserRoleSearchAPI.as_view(), name='search-user-role'),
    path('user-role/', dash_roles_views.UserRole.as_view(), name='create-delete-user-role'),
    path('', dash_roles_views.RoleAPI.as_view(), name="roles-list"),
    path('', dash_roles_views.RoleAPI.as_view(), name="roles-create"),
    path('csv/', dash_roles_views.RoleManagementCSV.as_view(), name="roles-csv"),
    path('<str:roles_id>/', dash_roles_views.RoleAPI.as_view(), name="roles-edit"),
    path('<str:roles_id>/', dash_roles_views.RoleAPI.as_view(), name="roles-delete"),

]
