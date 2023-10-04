from django.urls import path

from . import dash_task_view

urlpatterns = [
    path('', dash_task_view.TaskApi.as_view()),  # list task, create
    path('csv/', dash_task_view.TaskListCSV.as_view()),  # CSV
    path('<str:task_id>/', dash_task_view.TaskApi.as_view()),  # get task, edit, delete

    path('import/', dash_task_view.ImportTaskListCSV.as_view()),
    path('channel/', dash_task_view.ChannelDropdownAPI.as_view()),
    path('ig/', dash_task_view.IGDropdownAPI.as_view()),
    path('organization/', dash_task_view.OrganizationDropdownAPI.as_view()),
    path('level/', dash_task_view.LevelDropdownAPI.as_view()),
    path('task-types/', dash_task_view.TaskTypesDropDownAPI.as_view()),
    path('events/', dash_task_view.EventDropDownApi.as_view()),
]
