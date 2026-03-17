from django.urls import path

from . import dash_ig_view

urlpatterns = [
    path('', dash_ig_view.InterestGroupAPI.as_view()),  # for get data and create new interest groups
    path('request/', dash_ig_view.InterestGroupRequestAPI.as_view()),  # for submitting IG creation requests
    path('request/<str:pk>/', dash_ig_view.InterestGroupRequestAPI.as_view()),  # for updating IG request status
    path('list/', dash_ig_view.InterestGroupListApi.as_view()),  # for public listing without admin permission
    path('csv/', dash_ig_view.InterestGroupCSV.as_view()),  # for IG data CSV download
    path('<str:pk>/', dash_ig_view.InterestGroupAPI.as_view()),  # for edit and delete
    path('get/<str:pk>/', dash_ig_view.InterestGroupGetAPI.as_view()),  # for edit and delete
    path('<str:ig_id>/task-summary/', dash_ig_view.IGTaskSummaryAPI.as_view()),  # IG task activity summary
]
