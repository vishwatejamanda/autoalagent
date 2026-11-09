"""Events API: Server-Sent Events (SSE) stream for real-time progress and notifications."""

import asyncio
from fastapi import APIRouter
from starlette.responses import StreamingResponse

from services.event_bus import event_bus, sse_event_generator

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/stream")
async def stream_events():
    """Stream real-time server events (scan progress, applications, scoring, audit logs) via SSE."""
    subscriber_queue = event_bus.subscribe()
    return StreamingResponse(
        sse_event_generator(subscriber_queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
