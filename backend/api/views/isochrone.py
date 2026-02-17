"""Isochrone proxy — forwards requests to Valhalla and returns GeoJSON."""
import httpx
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from api.services.valhalla import get_isochrone


@require_http_methods(["GET"])
async def isochrone(request):
    """
    GET /api/isochrone?lat=X&lon=Y&time=N&costing=auto

    Proxies to Valhalla /isochrone and returns the GeoJSON FeatureCollection.
    Query params:
        lat     (float, required) — latitude of the origin point
        lon     (float, required) — longitude of the origin point
        time    (int,   required) — travel time contour in minutes
        costing (str,  optional) — Valhalla costing model, default "auto"
    """
    try:
        lat = float(request.GET["lat"])
        lon = float(request.GET["lon"])
        time = int(request.GET["time"])
    except KeyError as exc:
        return JsonResponse(
            {"error": f"Missing required query parameter: {exc.args[0]}"}, status=400
        )
    except ValueError:
        return JsonResponse(
            {"error": "lat and lon must be floats; time must be an integer"}, status=400
        )

    costing = request.GET.get("costing", "auto")

    try:
        result = await get_isochrone(lat, lon, time, costing)
    except httpx.HTTPStatusError as exc:
        return JsonResponse(
            {"error": f"Routing service returned {exc.response.status_code}"},
            status=502,
        )
    except httpx.RequestError as exc:
        return JsonResponse(
            {"error": f"Could not reach routing service: {exc}"},
            status=502,
        )

    return JsonResponse(result)
