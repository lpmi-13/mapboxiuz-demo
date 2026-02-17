"""Generate random UK routes by calling the Valhalla service concurrently."""
import asyncio

from api.services.valhalla import get_route
from api.utils.uk_coordinates import pick_random_pair


async def _fetch_single_route(origin: dict, destination: dict) -> dict:
    locations = [
        {"lat": origin["lat"], "lon": origin["lon"]},
        {"lat": destination["lat"], "lon": destination["lon"]},
    ]
    route_data = await get_route(locations)
    return {"origin": origin, "destination": destination, **route_data}


async def generate_routes(n: int = 3) -> list[dict]:
    """
    Generate *n* random UK routes concurrently.

    Each route dict contains: origin, destination, distance_km, duration_min,
    geometry (GeoJSON LineString), legs.

    Routes that fail (e.g. Valhalla unreachable) are silently dropped so the
    SSE stream continues to function with partial results.
    """
    pairs = [pick_random_pair() for _ in range(n)]
    tasks = [_fetch_single_route(origin, dest) for origin, dest in pairs]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]
