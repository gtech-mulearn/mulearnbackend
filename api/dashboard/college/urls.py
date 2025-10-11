from django.urls import path

from . import college_view

urlpatterns = [
    path('', college_view.CollegeApi.as_view()),
    path('change-college/', college_view.CollegeChangeAPI.as_view()),
    path('<str:college_code>/', college_view.CollegeApi.as_view()),
    
]
