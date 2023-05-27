from django.urls import path

from . import dash_task_view

urlpatterns = [
    path('', dash_task_view.TaskApi.as_view()),  # list task
    path('csv/', dash_task_view.TaskListCSV.as_view()),  # CSV
    path('create/', dash_task_view.TaskApi.as_view()),  # Create task
    path('edit/<str:pk>/', dash_task_view.TaskApi.as_view()),  # Edit task
    path('delete/<str:pk>/', dash_task_view.TaskApi.as_view())  # Delete task
]
