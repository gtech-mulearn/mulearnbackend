from django.urls import path, include

urlpatterns = [
    path('organisation/', include('api.protected.organisation.urls')),
    # Member creation for "Sign in with muLearn". Called by authserver only,
    # so that signup can live on auth.mulearn.org without duplicating the muid
    # and wallet/level/role logic that lives in this repo.
    path('identity/', include('api.protected.identity.urls')),
]
