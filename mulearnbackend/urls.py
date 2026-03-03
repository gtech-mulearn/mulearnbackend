from django.conf import settings
from django.urls import path, include, re_path
from django.views.static import serve
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from decouple import config as decouple_config

urlpatterns = [
    path("api/v1/", include("api.urls")),
    re_path(
        r"^muback-media/(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
    # OpenAPI schema (always available)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]

# Conditionally enable Swagger UI & Redoc
if decouple_config("ENABLE_SWAGGER", default=False, cast=bool):
    urlpatterns += [
        path(
            "api/docs/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "api/redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
        ),
    ]
