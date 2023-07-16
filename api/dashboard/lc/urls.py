from django.urls import path
from . import dash_lc_view

urlpatterns = [
    path('', dash_lc_view.LearningCircleListApi.as_view()),
    path('join/', dash_lc_view.LearningCircleAPI.as_view()),
    path('create/', dash_lc_view.LearningCircleAPI.as_view())
]