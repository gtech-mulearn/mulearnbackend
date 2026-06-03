from django.urls import path
from . import tasks_views

urlpatterns = [
    path("mine/", tasks_views.InternTaskMineAPI.as_view(), name="intern-tasks-mine"),
]
