"""Tests for the isochrone proxy endpoint."""
import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from django.test import AsyncClient

MOCK_ISOCHRONE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-0.2, 51.4], [-0.0, 51.6], [-0.2, 51.4]]],
            },
            "properties": {"contour": 15},
        }
    ],
}


@pytest.mark.django_db
class TestIsochrone:
    async def test_valid_request_returns_200(self):
        client = AsyncClient()
        with patch(
            "api.views.isochrone.get_isochrone",
            new=AsyncMock(return_value=MOCK_ISOCHRONE),
        ):
            response = await client.get(
                "/api/isochrone?lat=51.5074&lon=-0.1278&time=15"
            )

        assert response.status_code == 200

    async def test_response_is_feature_collection(self):
        client = AsyncClient()
        with patch(
            "api.views.isochrone.get_isochrone",
            new=AsyncMock(return_value=MOCK_ISOCHRONE),
        ):
            response = await client.get(
                "/api/isochrone?lat=51.5074&lon=-0.1278&time=15"
            )

        data = json.loads(response.content)
        assert data["type"] == "FeatureCollection"

    async def test_missing_lat_returns_400(self):
        client = AsyncClient()
        response = await client.get("/api/isochrone?lon=-0.1278&time=15")
        assert response.status_code == 400

    async def test_missing_lon_returns_400(self):
        client = AsyncClient()
        response = await client.get("/api/isochrone?lat=51.5&time=15")
        assert response.status_code == 400

    async def test_missing_time_returns_400(self):
        client = AsyncClient()
        response = await client.get("/api/isochrone?lat=51.5&lon=-0.1")
        assert response.status_code == 400

    async def test_invalid_lat_type_returns_400(self):
        client = AsyncClient()
        response = await client.get("/api/isochrone?lat=abc&lon=-0.1&time=15")
        assert response.status_code == 400

    async def test_custom_costing_forwarded(self):
        client = AsyncClient()
        mock_fn = AsyncMock(return_value=MOCK_ISOCHRONE)
        with patch("api.views.isochrone.get_isochrone", new=mock_fn):
            await client.get("/api/isochrone?lat=51.5&lon=-0.1&time=15&costing=bicycle")

        _, kwargs = mock_fn.call_args
        # costing is the 4th positional arg
        args = mock_fn.call_args.args
        assert args[3] == "bicycle"

    async def test_valhalla_error_returns_502(self):
        client = AsyncClient()
        mock_response = AsyncMock()
        mock_response.status_code = 400
        with patch(
            "api.views.isochrone.get_isochrone",
            new=AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "bad request", request=AsyncMock(), response=mock_response
                )
            ),
        ):
            response = await client.get("/api/isochrone?lat=51.5&lon=-0.1&time=15")

        assert response.status_code == 502

    async def test_post_not_allowed(self):
        client = AsyncClient()
        response = await client.post("/api/isochrone")
        assert response.status_code == 405
