from django.urls import path

from . import dash_ig_view, impact_project_view

urlpatterns = [
    path('', dash_ig_view.InterestGroupAPI.as_view()),  # for get data and create new interest groups
    path('request/', dash_ig_view.InterestGroupRequestAPI.as_view()),  # for submitting IG creation requests
    path('request/<str:pk>/', dash_ig_view.InterestGroupRequestAPI.as_view()),  # PATCH: admin status update | DELETE: cancel request
    path('list/', dash_ig_view.InterestGroupListApi.as_view()),  # for public listing without admin permission
    path('csv/', dash_ig_view.InterestGroupCSV.as_view()),  # for IG data CSV download
    path('impact-projects/public/', impact_project_view.PublicImpactProjectListAPI.as_view()),
    path('<str:ig_id>/impact-projects/', impact_project_view.ImpactProjectListCreateAPI.as_view()),
    path('<str:ig_id>/impact-projects/<str:project_id>/', impact_project_view.ImpactProjectDetailAPI.as_view()),
    path('<str:ig_id>/impact-projects/<str:project_id>/image/', impact_project_view.ImpactProjectImageAPI.as_view()),
    path('<str:pk>/cover-image/', dash_ig_view.InterestGroupImageAPI.as_view(), {'image_type': 'cover'}),
    path('<str:pk>/icon-image/', dash_ig_view.InterestGroupImageAPI.as_view(), {'image_type': 'icon'}),
    path('<str:pk>/', dash_ig_view.InterestGroupAPI.as_view()),  # for edit and delete
    path('get/<str:pk>/', dash_ig_view.InterestGroupGetAPI.as_view()),  # for edit and delete
    path('<str:pk>/join/', dash_ig_view.InterestGroupMembershipAPI.as_view()),
    path('<str:pk>/leave/', dash_ig_view.InterestGroupMembershipAPI.as_view()),
]
