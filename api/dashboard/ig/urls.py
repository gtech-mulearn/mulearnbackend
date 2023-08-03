from django.urls import path

from . import dash_ig_view

urlpatterns = [
    path('', dash_ig_view.InterestGroupAPI.as_view()),  # for get data and create new interest groups
    path('list/', dash_ig_view.InterestGroupListApi.as_view()),  # for get data and create new interest groups
    path('csv/', dash_ig_view.InterestGroupCSV.as_view()),  # for IG data CSV download
    path('<str:pk>/', dash_ig_view.InterestGroupAPI.as_view()),  # for edit and delete
    path('get/<str:pk>/', dash_ig_view.InterestGroupGetAPI.as_view()),  # for edit and delete
]
