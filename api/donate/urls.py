from . import views
from django.urls import path

urlpatterns = [
    path('order/', views.RazorPayOrderAPI.as_view()),
    path('verify/', views.RazorPayVerification.as_view())
]