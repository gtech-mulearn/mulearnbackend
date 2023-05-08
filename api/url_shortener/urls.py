from django.urls import path
from . import url_shortener_view


urlpatterns = [
    path('create-shorten-url/', url_shortener_view.CreateShortenUrl.as_view()),
    path('edit-shorten-url/<str:url_id>/', url_shortener_view.EditShortenUrl.as_view()),
    path('show-shorten-urls/', url_shortener_view.ShowShortenUrls.as_view()),
    path('delete-shorten-url/<str:url_id>/', url_shortener_view.DeleteShortenUrl.as_view()),
]
