from django.urls import path
from . import portal_views

urlpatterns = [
    # path('add', portal_views.AddPortal.as_view()),
    path('user/authorize', portal_views.UserMailTokenValidation.as_view()),

]
