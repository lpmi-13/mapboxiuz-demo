"""Tests for the health-check endpoint."""
import json

import pytest
from django.test import AsyncClient


@pytest.mark.django_db
class TestHealthz:
    async def test_returns_200(self):
        client = AsyncClient()
        response = await client.get("/healthz")
        assert response.status_code == 200

    async def test_returns_json_ok(self):
        client = AsyncClient()
        response = await client.get("/healthz")
        data = json.loads(response.content)
        assert data == {"status": "ok"}

    async def test_content_type_is_json(self):
        client = AsyncClient()
        response = await client.get("/healthz")
        assert "application/json" in response["Content-Type"]
