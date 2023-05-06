from django.urls import path

from .dash_user_views import UserAPI, CollegePaginationTestAPI

urlpatterns = [
    path('', UserAPI.as_view(), name='user-api'),
    path('get-college-test-pagination/', CollegePaginationTestAPI.as_view(),name='get_college_test_pagination'),
]
