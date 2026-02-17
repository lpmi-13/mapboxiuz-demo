from django.urls import include, path

from api.views.health import healthz

urlpatterns = [
    path("healthz", healthz),
    path("api/", include("api.urls")),
]
