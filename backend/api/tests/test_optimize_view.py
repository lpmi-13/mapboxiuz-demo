"""Tests for the route optimization endpoint."""
import json
from unittest.mock import AsyncMock, patch

import pytest
from django.test import AsyncClient

STOPS = [
    {"lat": 51.5074, "lon": -0.1278, "name": "London"},
    {"lat": 53.4808, "lon": -2.2426, "name": "Manchester"},
    {"lat": 55.9533, "lon": -3.1883, "name": "Edinburgh"},
]

MOCK_MATRIX = [
    [0.0, 320.5, 640.0],
    [320.5, 0.0, 330.0],
    [640.0, 330.0, 0.0],
]

MOCK_ROUTE = {
    "geometry": {
        "type": "LineString",
        "coordinates": [[-0.12, 51.5], [-2.24, 53.48], [-3.18, 55.95]],
    },
    "distance_km": 650.5,
    "duration_min": 380.0,
    "legs": [
        {"distance_km": 320.5, "duration_min": 185.0},
        {"distance_km": 330.0, "duration_min": 195.0},
    ],
}


def _post(client, body):
    return client.post(
        "/api/optimize-route",
        data=json.dumps(body),
        content_type="application/json",
    )


@pytest.mark.django_db
class TestOptimizeRoute:
    async def test_valid_request_returns_200(self):
        client = AsyncClient()
        with patch(
            "api.views.optimize.get_matrix", new=AsyncMock(return_value=MOCK_MATRIX)
        ), patch(
            "api.views.optimize.get_route", new=AsyncMock(return_value=MOCK_ROUTE)
        ):
            response = await _post(client, {"stops": STOPS})

        assert response.status_code == 200

    async def test_response_has_ordered_stops_and_route(self):
        client = AsyncClient()
        with patch(
            "api.views.optimize.get_matrix", new=AsyncMock(return_value=MOCK_MATRIX)
        ), patch(
            "api.views.optimize.get_route", new=AsyncMock(return_value=MOCK_ROUTE)
        ):
            response = await _post(client, {"stops": STOPS})

        data = json.loads(response.content)
        assert "ordered_stops" in data
        assert "route" in data
        assert len(data["ordered_stops"]) == 3

    async def test_route_contains_geometry(self):
        client = AsyncClient()
        with patch(
            "api.views.optimize.get_matrix", new=AsyncMock(return_value=MOCK_MATRIX)
        ), patch(
            "api.views.optimize.get_route", new=AsyncMock(return_value=MOCK_ROUTE)
        ):
            response = await _post(client, {"stops": STOPS})

        data = json.loads(response.content)
        assert data["route"]["geometry"]["type"] == "LineString"

    async def test_fewer_than_two_stops_returns_400(self):
        client = AsyncClient()
        response = await _post(client, {"stops": [STOPS[0]]})
        assert response.status_code == 400

    async def test_empty_stops_returns_400(self):
        client = AsyncClient()
        response = await _post(client, {"stops": []})
        assert response.status_code == 400

    async def test_invalid_json_returns_400(self):
        client = AsyncClient()
        response = await client.post(
            "/api/optimize-route",
            data="not json",
            content_type="application/json",
        )
        assert response.status_code == 400

    async def test_stop_missing_lat_returns_400(self):
        client = AsyncClient()
        bad_stops = [{"lon": -0.12, "name": "A"}, {"lat": 53.4, "lon": -2.2, "name": "B"}]
        response = await _post(client, {"stops": bad_stops})
        assert response.status_code == 400

    async def test_round_trip_flag_accepted(self):
        client = AsyncClient()
        with patch(
            "api.views.optimize.get_matrix", new=AsyncMock(return_value=MOCK_MATRIX)
        ), patch(
            "api.views.optimize.get_route", new=AsyncMock(return_value=MOCK_ROUTE)
        ):
            response = await _post(
                client, {"stops": STOPS, "round_trip": True, "fixed_start": True}
            )

        assert response.status_code == 200

    async def test_get_method_not_allowed(self):
        client = AsyncClient()
        response = await client.get("/api/optimize-route")
        assert response.status_code == 405
