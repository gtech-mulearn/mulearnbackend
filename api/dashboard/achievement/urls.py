from django.urls import path

urlpatterns = [
    path('achievements/', qseverse_views.QseverseAPIView.as_view(), name='achievements'),
]