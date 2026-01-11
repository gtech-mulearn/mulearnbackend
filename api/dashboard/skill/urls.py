from django.urls import path
from . import skill_views

urlpatterns = [
    # Skill CRUD
    path('', skill_views.SkillListAPI.as_view(), name='skill-list'),
    path('create/', skill_views.SkillCreateAPI.as_view(), name='skill-create'),
    path('dropdown/', skill_views.SkillDropdownAPI.as_view(), name='skill-dropdown'),
    path('<str:skill_id>/', skill_views.SkillDetailAPI.as_view(), name='skill-detail'),
    path('<str:skill_id>/tasks/', skill_views.SkillTasksAPI.as_view(), name='skill-tasks'),
]
