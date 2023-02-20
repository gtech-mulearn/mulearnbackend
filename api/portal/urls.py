from django.urls import path
from . import portal_views

urlpatterns = [
    # path('add', portal_views.AddPortal.as_view()),
    path('mu-id/validate',portal_views.MuidValidate.as_view()),
]
