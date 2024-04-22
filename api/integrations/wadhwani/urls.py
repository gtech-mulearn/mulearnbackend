from django.urls import path

from . import wadhwani_views

# app_name will help us do a reverse look-up latter.
urlpatterns = [
    path('auth-token/', wadhwani_views.WadhwaniAuthToken.as_view(), name='auth_token'),
    path('user-login/', wadhwani_views.WadhwaniUserLogin.as_view(), name='user_login'),
    path('course-details/', wadhwani_views.WadhwaniCourseDetails.as_view(), name='course_details'),
    path('course-enroll-status/', wadhwani_views.WadhwaniCourseEnrollStatus.as_view(), name='course_enroll_status'),
    path('course-quiz-data/', wadhwani_views.WadhwaniCourseQuizData.as_view(), name='course_quiz_data'),
]