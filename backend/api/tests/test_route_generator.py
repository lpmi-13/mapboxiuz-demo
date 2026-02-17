"""Tests for the route generator service."""
from unittest.mock import AsyncMock, patch

import pytest

from api.services.route_generator import generate_routes

MOCK_ROUTE = {
    "geometry": {"type": "LineString", "coordinates": [[-0.12, 51.5], [-2.24, 53.48]]},
    "distance_km": 320.5,
    "duration_min": 185.0,
    "legs": [{"distance_km": 320.5, "duration_min": 185.0}],
}


class TestGenerateRoutes:
    async def test_returns_list_of_routes(self):
        with patch(
            "api.services.route_generator.get_route", new=AsyncMock(return_value=MOCK_ROUTE)
        ):
            routes = await generate_routes(n=3)

        assert isinstance(routes, list)
        assert len(routes) == 3

    async def test_route_has_origin_and_destination(self):
        with patch(
            "api.services.route_generator.get_route", new=AsyncMock(return_value=MOCK_ROUTE)
        ):
            routes = await generate_routes(n=1)

        route = routes[0]
        assert "origin" in route
        assert "destination" in route
        assert "name" in route["origin"]
        assert "lat" in route["origin"]
        assert "lon" in route["origin"]

    async def test_route_has_geometry_and_metrics(self):
        with patch(
            "api.services.route_generator.get_route", new=AsyncMock(return_value=MOCK_ROUTE)
        ):
            routes = await generate_routes(n=1)

        route = routes[0]
        assert route["geometry"]["type"] == "LineString"
        assert "distance_km" in route
        assert "duration_min" in route

    async def test_failed_routes_are_dropped(self):
        """If Valhalla fails for some routes the rest are still returned."""
        call_count = 0

        async def flaky_get_route(locations, costing="auto"):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Valhalla error")
            return MOCK_ROUTE

        with patch("api.services.route_generator.get_route", side_effect=flaky_get_route):
            routes = await generate_routes(n=3)

        # One route failed, so we get 2 instead of 3
        assert len(routes) == 2

    async def test_all_failed_returns_empty_list(self):
        with patch(
            "api.services.route_generator.get_route",
            new=AsyncMock(side_effect=Exception("down")),
        ):
            routes = await generate_routes(n=3)

        assert routes == []

    async def test_n_parameter_controls_count(self):
        with patch(
            "api.services.route_generator.get_route", new=AsyncMock(return_value=MOCK_ROUTE)
        ):
            routes = await generate_routes(n=2)

        assert len(routes) == 2
