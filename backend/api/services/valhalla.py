"""Async HTTP client for the Valhalla routing engine."""
import httpx
from django.conf import settings


def _get_client() -> httpx.AsyncClient:
    """Create a one-shot async client bound to the configured Valhalla URL."""
    return httpx.AsyncClient(base_url=settings.VALHALLA_URL, timeout=30.0)


def _decode_polyline(encoded: str, precision: int = 6) -> list[list[float]]:
    """Decode a Valhalla/Google encoded polyline to [[lon, lat], ...] GeoJSON order."""
    result: list[list[float]] = []
    index = 0
    lat = 0
    lng = 0
    factor = 10**precision

    while index < len(encoded):
        shift, result_val = 0, 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result_val |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result_val >> 1) if (result_val & 1) else (result_val >> 1)
        lat += dlat

        shift, result_val = 0, 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result_val |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result_val >> 1) if (result_val & 1) else (result_val >> 1)
        lng += dlng

        # GeoJSON convention: [longitude, latitude]
        result.append([lng / factor, lat / factor])

    return result


async def get_route(
    locations: list[dict], costing: str = "auto"
) -> dict:
    """
    Call Valhalla POST /route.

    Each location dict must have 'lat' and 'lon' keys.
    Returns a normalized dict with GeoJSON geometry, distance_km, duration_min, legs.
    """
    payload = {
        "locations": locations,
        "costing": costing,
        "directions_options": {"units": "kilometers"},
    }
    async with _get_client() as client:
        response = await client.post("/route", json=payload)
        response.raise_for_status()

    data = response.json()
    trip = data["trip"]
    legs = trip["legs"]

    # Concatenate decoded shapes from all legs
    coords: list[list[float]] = []
    for leg in legs:
        decoded = _decode_polyline(leg["shape"])
        if coords and decoded:
            # Skip first point of subsequent legs — it duplicates the previous end
            decoded = decoded[1:]
        coords.extend(decoded)

    distance_km = round(trip["summary"]["length"], 2)
    duration_min = round(trip["summary"]["time"] / 60, 1)

    return {
        "geometry": {"type": "LineString", "coordinates": coords},
        "distance_km": distance_km,
        "duration_min": duration_min,
        "legs": [
            {
                "distance_km": round(leg["summary"]["length"], 2),
                "duration_min": round(leg["summary"]["time"] / 60, 1),
            }
            for leg in legs
        ],
    }


async def get_matrix(
    sources: list[dict], targets: list[dict], costing: str = "auto"
) -> list[list[float]]:
    """
    Call Valhalla POST /sources_to_targets.

    Returns an N×M matrix of distances in kilometres.
    """
    payload = {
        "sources": sources,
        "targets": targets,
        "costing": costing,
        "directions_options": {"units": "kilometers"},
    }
    async with _get_client() as client:
        response = await client.post("/sources_to_targets", json=payload)
        response.raise_for_status()

    data = response.json()
    return [
        [cell.get("distance", float("inf")) for cell in row]
        for row in data["sources_to_targets"]
    ]


async def get_isochrone(
    lat: float, lon: float, time: int, costing: str = "auto"
) -> dict:
    """
    Call Valhalla POST /isochrone.

    Returns the raw GeoJSON FeatureCollection from Valhalla.
    """
    payload = {
        "locations": [{"lat": lat, "lon": lon}],
        "costing": costing,
        "contours": [{"time": time}],
        "polygons": True,
    }
    async with _get_client() as client:
        response = await client.post("/isochrone", json=payload)
        response.raise_for_status()

    return response.json()
