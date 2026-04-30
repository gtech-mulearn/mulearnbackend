from django.urls import path

from . import views

urlpatterns = [
    path('', views.EventCollectionAPI.as_view()),
    path('<str:event_id>/', views.EventDetailAPI.as_view()),
]
