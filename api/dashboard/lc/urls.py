from django.urls import path

from . import dash_lc_view

urlpatterns = [
    path('', dash_lc_view.UserLearningCircleListApi.as_view()),
    path('list-members/<str:circle_name>/', dash_lc_view.LearningCircleListMembersApi.as_view()),
    # path('invite/', dash_lc_view.LearningCircleInviteLeadAPI.as_view()),
    path('list/', dash_lc_view.LearningCircleMainApi.as_view()),
    path('data/', dash_lc_view.LearningCircleDataAPI.as_view()),
    path('list-all/', dash_lc_view.TotalLearningCircleListApi.as_view()),
    path('list-all/<str:circle_code>/', dash_lc_view.TotalLearningCircleListApi.as_view()),
    path('create/', dash_lc_view.LearningCircleCreateApi.as_view()),
    path('meet/<str:circle_id>/', dash_lc_view.LearningCircleMeetAPI.as_view()),
    path('join/<str:circle_id>/', dash_lc_view.LearningCircleJoinApi.as_view()),
    path('<str:circle_id>/', dash_lc_view.LearningCircleHomeApi.as_view()),
    path('<str:circle_id>/<str:member_id>/', dash_lc_view.LearningCircleHomeApi.as_view()),
    path('lead/<str:circle_id>/<str:lead_id>/', dash_lc_view.LearningCircleLeadTransfer.as_view()),


]
