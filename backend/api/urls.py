from django.urls import path

from api.views.isochrone import isochrone
from api.views.optimize import optimize_route
from api.views.sse import route_stream

urlpatterns = [
    path("routes/stream", route_stream),
    path("optimize-route", optimize_route),
    path("isochrone", isochrone),
]
