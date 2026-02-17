"""Route optimization endpoint — solves TSP over user-supplied stops."""
import json

import httpx
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from api.services.optimizer import solve_tsp
from api.services.valhalla import get_matrix, get_route


@csrf_exempt
@require_http_methods(["POST"])
async def optimize_route(request):
    """
    POST /api/optimize-route

    Request body:
        {
            "stops": [{"lat": float, "lon": float, "name": str}, ...],
            "fixed_start": bool,   // keep stops[0] as the departure point
            "round_trip": bool     // append start to end for a loop
        }

    Response:
        {
            "ordered_stops": [...],
            "route": {"geometry": GeoJSON, "distance_km": float, "duration_min": float, "legs": [...]}
        }
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    stops: list[dict] = body.get("stops", [])
    fixed_start: bool = bool(body.get("fixed_start", False))
    round_trip: bool = bool(body.get("round_trip", False))

    if len(stops) < 2:
        return JsonResponse({"error": "At least 2 stops are required"}, status=400)

    for i, stop in enumerate(stops):
        if "lat" not in stop or "lon" not in stop:
            return JsonResponse(
                {"error": f"Stop {i} is missing 'lat' or 'lon'"}, status=400
            )

    locations = [{"lat": s["lat"], "lon": s["lon"]} for s in stops]

    try:
        matrix = await get_matrix(locations, locations)
        order = solve_tsp(matrix, fixed_start=fixed_start, round_trip=round_trip)

        # Deduplicate consecutive identical indices (can arise from round_trip)
        ordered_locations = [locations[i] for i in order if i < len(locations)]
        route_data = await get_route(ordered_locations)
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

    ordered_stops = [stops[i] for i in order if i < len(stops)]
    return JsonResponse({"ordered_stops": ordered_stops, "route": route_data})
