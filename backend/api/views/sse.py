"""Server-Sent Events endpoint — streams 3 random UK routes every 10 seconds."""
import asyncio
import json

from django.http import StreamingHttpResponse

from api.services.route_generator import generate_routes


async def _event_stream():
    """
    Async generator that yields SSE-formatted frames indefinitely.

    Each frame contains a JSON array of route objects.
    Errors are surfaced as a JSON object so the client can display them.
    """
    while True:
        try:
            routes = await generate_routes(n=3)
            payload = json.dumps(routes)
        except Exception as exc:  # noqa: BLE001
            payload = json.dumps({"error": str(exc)})

        yield f"data: {payload}\n\n"
        await asyncio.sleep(10)


async def route_stream(request):
    """
    GET /api/routes/stream

    Returns a long-lived text/event-stream response.
    Nginx must be configured with proxy_buffering off and a long read timeout.
    """
    response = StreamingHttpResponse(
        _event_stream(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # disable Nginx buffering
    return response
