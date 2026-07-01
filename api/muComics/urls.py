from django.urls import path, include

urlpatterns = [
    path('comics/', include('api.muComics.comic.urls')),
]
