from django.urls import path
from . import tasks_views

urlpatterns = [
    path("categories/", tasks_views.InternTaskCategoryAPI.as_view(), name="intern-tasks-categories"),
    path("mine/", tasks_views.InternTaskMineAPI.as_view(), name="intern-tasks-mine"),
    # Canonical task update path: PATCH /tasks/<task_id>/
    path("<str:task_id>/", tasks_views.InternTaskSubmitAPI.as_view(), name="intern-tasks-update"),
    # /submit/ kept for backward compat
    path("<str:task_id>/submit/", tasks_views.InternTaskSubmitAPI.as_view(), name="intern-tasks-submit"),
    path("<str:task_id>/detail/", tasks_views.InternTaskDetailAPI.as_view(), name="intern-tasks-detail"),
]
