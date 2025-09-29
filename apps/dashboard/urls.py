from django.urls import path, include
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Authentication endpoints
    path(
        'csrf/',
        views.get_csrf_token,
        name='csrf-token'
    ),
    path(
        'auth/login/',
        views.login_view,
        name='login'
    ),
    path(
        'auth/signup/',
        views.signup_view,
        name='signup'
    ),
    path(
        'auth/logout/',
        views.logout_view,
        name='logout'
    ),
    path(
        'auth/user/',
        views.current_user_view,
        name='current-user'
    ),
    
    # User Profile endpoints
    path(
        'profile/user-profile/',
        views.UserProfileRetrieveUpdateView.as_view(),
        name='user-profile'
    ),
    
    # Alternative endpoint for backward compatibility
    path(
        'profile/user-profile-legacy/',
        views.user_profile_view,
        name='user-profile-legacy'
    ),
    
    # Profile summary endpoint
    path(
        'profile/summary/',
        views.user_profile_summary,
        name='user-profile-summary'
    ),
    
    # Granular Bio endpoint
    path(
        'profile/bio/',
        views.update_bio,
        name='update-bio'
    ),
    
    # Granular Projects endpoints
    path(
        'profile/projects/',
        views.projects_list_create,
        name='projects-list-create'
    ),
    path(
        'profile/projects/<int:project_id>/',
        views.project_detail,
        name='project-detail'
    ),
    
    # Granular Experience endpoints
    path(
        'profile/experience/',
        views.experience_list_create,
        name='experience-list-create'
    ),
    path(
        'profile/experience/<int:experience_id>/',
        views.experience_detail,
        name='experience-detail'
    ),
]