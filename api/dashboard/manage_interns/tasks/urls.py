from django.urls import path
from . import tasks_views

urlpatterns = [
    path("", tasks_views.ManageInternTaskAPI.as_view(), name="manage-intern-task-list-create"),
    path("<str:task_id>/", tasks_views.ManageInternTaskAPI.as_view(), name="manage-intern-task-update-delete"),
    path("<str:task_id>/verify/", tasks_views.ManageInternTaskVerifyAPI.as_view(), name="manage-intern-task-verify"),
]
