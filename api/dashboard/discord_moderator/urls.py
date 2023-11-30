from django.urls import path

from . import discord_mod_views

urlpatterns = [
    path('tasklist/', discord_mod_views.TaskList.as_view()),
    path('pendingcounts/', discord_mod_views.PendingTasks.as_view()),
    
]
