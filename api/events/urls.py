from django.urls import path
from .views import UnifiedEventAPI

urlpatterns = [
    path('', UnifiedEventAPI.as_view(), name='unified-events'),
    path('<str:event_id>/', UnifiedEventAPI.as_view(), name='unified-events-detail'),
]
