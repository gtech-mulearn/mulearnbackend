from django.urls import path

from . import dash_ig_view

urlpatterns = [
    path('', dash_ig_view.InterestGroupAPI.as_view()), # for get data and create new interest groups
    path('/<str:pk>/', dash_ig_view.InterestGroupAPI.as_view()), # for edit and delete
]