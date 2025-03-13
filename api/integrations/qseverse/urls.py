from django.urls import path
from . import qseverse_views
urlpatterns = [
    path('achievements/', qseverse_views.QseverseAPIView.as_view(), name='achievements'),
]