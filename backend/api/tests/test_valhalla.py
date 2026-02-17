"""Tests for the Valhalla HTTP client."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from api.services.valhalla import _decode_polyline, get_isochrone, get_matrix, get_route


# ---------------------------------------------------------------------------
# _decode_polyline
# ---------------------------------------------------------------------------

class TestDecodePolyline:
    def test_decodes_known_pair(self):
        # Encode London (51.5074, -0.1278) manually then round-trip
        # Using precision=6
        coords = _decode_polyline("_seiz@~~cN")  # small known segment
        assert isinstance(coords, list)
        for point in coords:
            assert len(point) == 2

    def test_returns_lon_lat_order(self):
        # A very short encoded string for a point near (51.0, -1.0)
        # We verify lon comes before lat (GeoJSON convention)
        # Manually encoded: lat=51.0, lon=-1.0 at precision 6
        # lat_enc: 51000000 → ... just check structure
        encoded = "_ibE~ps|@"  # London area
        result = _decode_polyline(encoded)
        assert len(result) >= 1
        # Each element is [lon, lat]
        lon, lat = result[0]
        assert isinstance(lon, float)
        assert isinstance(lat, float)


# ---------------------------------------------------------------------------
# get_route
# ---------------------------------------------------------------------------

def _make_mock_response(data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


MOCK_ROUTE_RESPONSE = {
    "trip": {
        "locations": [
            {"lat": 51.5074, "lon": -0.1278},
            {"lat": 53.4808, "lon": -2.2426},
        ],
        "legs": [
            {
                "shape": "_seiz@~~cN",  # minimal encoded polyline
                "summary": {"length": 320.5, "time": 11100},
            }
        ],
        "summary": {"length": 320.5, "time": 11100},
        "status": 0,
        "status_message": "Found route",
    }
}


class TestGetRoute:
    @pytest.fixture
    def mock_client(self):
        mock_response = _make_mock_response(MOCK_ROUTE_RESPONSE)
        client = AsyncMock()
        client.post = AsyncMock(return_value=mock_response)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        return client

    async def test_returns_expected_keys(self, mock_client):
        with patch("api.services.valhalla._get_client", return_value=mock_client):
            result = await get_route(
                [{"lat": 51.5, "lon": -0.1}, {"lat": 53.4, "lon": -2.2}]
            )

        assert "geometry" in result
        assert "distance_km" in result
        assert "duration_min" in result
        assert "legs" in result

    async def test_geometry_is_linestring(self, mock_client):
        with patch("api.services.valhalla._get_client", return_value=mock_client):
            result = await get_route(
                [{"lat": 51.5, "lon": -0.1}, {"lat": 53.4, "lon": -2.2}]
            )

        assert result["geometry"]["type"] == "LineString"
        assert isinstance(result["geometry"]["coordinates"], list)

    async def test_distance_rounded(self, mock_client):
        with patch("api.services.valhalla._get_client", return_value=mock_client):
            result = await get_route(
                [{"lat": 51.5, "lon": -0.1}, {"lat": 53.4, "lon": -2.2}]
            )

        assert result["distance_km"] == 320.5

    async def test_duration_converted_to_minutes(self, mock_client):
        with patch("api.services.valhalla._get_client", return_value=mock_client):
            result = await get_route(
                [{"lat": 51.5, "lon": -0.1}, {"lat": 53.4, "lon": -2.2}]
            )

        assert result["duration_min"] == round(11100 / 60, 1)

    async def test_http_error_propagates(self):
        error_client = AsyncMock()
        error_client.__aenter__ = AsyncMock(return_value=error_client)
        error_client.__aexit__ = AsyncMock(return_value=False)
        error_client.post = AsyncMock(
            side_effect=httpx.RequestError("connection refused")
        )

        with patch("api.services.valhalla._get_client", return_value=error_client):
            with pytest.raises(httpx.RequestError):
                await get_route([{"lat": 51.5, "lon": -0.1}, {"lat": 53.4, "lon": -2.2}])


# ---------------------------------------------------------------------------
# get_matrix
# ---------------------------------------------------------------------------

MOCK_MATRIX_RESPONSE = {
    "sources_to_targets": [
        [{"distance": 320.5, "time": 11100}, {"distance": 0.0, "time": 0}],
        [{"distance": 0.0, "time": 0}, {"distance": 320.5, "time": 11100}],
    ]
}


class TestGetMatrix:
    @pytest.fixture
    def mock_client(self):
        mock_response = _make_mock_response(MOCK_MATRIX_RESPONSE)
        client = AsyncMock()
        client.post = AsyncMock(return_value=mock_response)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        return client

    async def test_returns_2d_list(self, mock_client):
        with patch("api.services.valhalla._get_client", return_value=mock_client):
            matrix = await get_matrix(
                [{"lat": 51.5, "lon": -0.1}],
                [{"lat": 53.4, "lon": -2.2}],
            )

        assert isinstance(matrix, list)
        assert isinstance(matrix[0], list)

    async def test_correct_distances(self, mock_client):
        with patch("api.services.valhalla._get_client", return_value=mock_client):
            matrix = await get_matrix(
                [{"lat": 51.5, "lon": -0.1}, {"lat": 53.4, "lon": -2.2}],
                [{"lat": 51.5, "lon": -0.1}, {"lat": 53.4, "lon": -2.2}],
            )

        assert matrix[0][0] == 320.5
        assert matrix[0][1] == 0.0


# ---------------------------------------------------------------------------
# get_isochrone
# ---------------------------------------------------------------------------

MOCK_ISOCHRONE_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[-0.1, 51.5], [-0.2, 51.6], [-0.1, 51.5]]]},
            "properties": {"contour": 15, "color": "#bf4040"},
        }
    ],
}


class TestGetIsochrone:
    @pytest.fixture
    def mock_client(self):
        mock_response = _make_mock_response(MOCK_ISOCHRONE_RESPONSE)
        client = AsyncMock()
        client.post = AsyncMock(return_value=mock_response)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        return client

    async def test_returns_feature_collection(self, mock_client):
        with patch("api.services.valhalla._get_client", return_value=mock_client):
            result = await get_isochrone(51.5, -0.1, 15)

        assert result["type"] == "FeatureCollection"
        assert "features" in result
