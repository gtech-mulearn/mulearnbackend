from django.urls import path

from . import college_view

urlpatterns = [
    path('', college_view.CollegeApi.as_view()),
    path('delete/<str:college_id>/', college_view.CollegeUpdateDeleteApi.as_view()),
    path('<str:college_code>/', college_view.CollegeApi.as_view())
]
