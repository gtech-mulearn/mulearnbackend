from django.urls import path, include

urlpatterns = [
    path('comics/', include('api.muComics.comic.urls')),
    path('comments/', include('api.muComics.comment.urls')),
    path('chapters/', include('api.muComics.chapter.urls')),
    path('reader/', include('api.muComics.reader.urls')),
]
