from django.urls import path

from . import college_view

urlpatterns = [
    path('', college_view.CollegeApi.as_view())
]
