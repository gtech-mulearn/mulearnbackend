from django.urls import path

from . import views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('', views.ArticleView.as_view()),
]
