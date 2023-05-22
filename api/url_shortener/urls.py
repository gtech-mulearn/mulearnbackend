from django.urls import path
from . import url_shortener_view


urlpatterns = [
    path('create/', url_shortener_view.CreateShortenUrl.as_view()),
    path('edit/<str:url_id>/', url_shortener_view.EditShortenUrl.as_view()),
    path('list/', url_shortener_view.ShowShortenUrls.as_view()),
    path('delete/<str:url_id>/', url_shortener_view.DeleteShortenUrl.as_view()),
]
