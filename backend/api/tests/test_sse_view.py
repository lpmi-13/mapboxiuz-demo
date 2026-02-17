"""Tests for the SSE route stream endpoint."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from django.test import AsyncClient

MOCK_ROUTES = [
    {
        "origin": {"name": "London", "lat": 51.5074, "lon": -0.1278},
        "destination": {"name": "Manchester", "lat": 53.4808, "lon": -2.2426},
        "geometry": {
            "type": "LineString",
            "coordinates": [[-0.12, 51.5], [-2.24, 53.48]],
        },
        "distance_km": 320.5,
        "duration_min": 185.0,
        "legs": [{"distance_km": 320.5, "duration_min": 185.0}],
    }
]


class TestEventStreamGenerator:
    """Unit-test the internal generator directly."""

    async def test_first_frame_is_valid_sse(self):
        from api.views.sse import _event_stream

        with patch(
            "api.views.sse.generate_routes", new=AsyncMock(return_value=MOCK_ROUTES)
        ), patch("api.views.sse.asyncio.sleep", new=AsyncMock()):
            gen = _event_stream()
            frame = await gen.__anext__()

        assert frame.startswith("data: ")
        assert frame.endswith("\n\n")

    async def test_frame_body_is_valid_json(self):
        from api.views.sse import _event_stream

        with patch(
            "api.views.sse.generate_routes", new=AsyncMock(return_value=MOCK_ROUTES)
        ), patch("api.views.sse.asyncio.sleep", new=AsyncMock()):
            gen = _event_stream()
            frame = await gen.__anext__()

        payload = frame[len("data: ") : -2]  # strip prefix and \n\n
        data = json.loads(payload)
        assert data == MOCK_ROUTES

    async def test_error_yields_error_frame(self):
        from api.views.sse import _event_stream

        with patch(
            "api.views.sse.generate_routes",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ), patch("api.views.sse.asyncio.sleep", new=AsyncMock()):
            gen = _event_stream()
            frame = await gen.__anext__()

        payload = json.loads(frame[len("data: ") : -2])
        assert "error" in payload


@pytest.mark.django_db
class TestRouteStreamView:
    async def test_content_type_is_event_stream(self):
        client = AsyncClient()

        with patch(
            "api.views.sse.generate_routes", new=AsyncMock(return_value=MOCK_ROUTES)
        ), patch("api.views.sse.asyncio.sleep", new=AsyncMock()):
            response = await client.get("/api/routes/stream")

        assert response["Content-Type"] == "text/event-stream"

    async def test_cache_control_header(self):
        client = AsyncClient()

        with patch(
            "api.views.sse.generate_routes", new=AsyncMock(return_value=MOCK_ROUTES)
        ), patch("api.views.sse.asyncio.sleep", new=AsyncMock()):
            response = await client.get("/api/routes/stream")

        assert response["Cache-Control"] == "no-cache"

    async def test_nginx_buffering_disabled(self):
        client = AsyncClient()

        with patch(
            "api.views.sse.generate_routes", new=AsyncMock(return_value=MOCK_ROUTES)
        ), patch("api.views.sse.asyncio.sleep", new=AsyncMock()):
            response = await client.get("/api/routes/stream")

        assert response["X-Accel-Buffering"] == "no"
