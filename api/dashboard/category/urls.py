from django.urls import path

from . import category_views

urlpatterns = [
    path('', category_views.CategoryAPI.as_view()),
    path('<str:category_id>/', category_views.CategoryAPI.as_view()),
]