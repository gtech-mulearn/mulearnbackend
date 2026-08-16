from django.urls import path

from . import views

urlpatterns = [
    path('', views.CommunityPartnerListCreateAPI.as_view()),
    path('<str:partner_id>/', views.CommunityPartnerDetailAPI.as_view()),
]
