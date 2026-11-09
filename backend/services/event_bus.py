"""Real-time Server-Sent Events (SSE) event bus for scans, applications, and logs."""

import asyncio
import json
import logging
from typing import AsyncGenerator, Set

logger = logging.getLogger(__name__)


class EventBus:
    """Pub/Sub event broadcaster for real-time SSE streaming to the frontend."""

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        """Register a new SSE client subscriber queue."""
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        """Unregister an SSE client queue."""
        self._subscribers.discard(q)

    async def publish(self, event_type: str, data: dict) -> None:
        """Broadcast an event to all connected SSE clients."""
        payload = {
            "type": event_type,
            "data": data,
        }
        dead_queues = []
        for q in self._subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead_queues.append(q)
            except Exception:
                dead_queues.append(q)

        for q in dead_queues:
            self._subscribers.discard(q)


# Singleton instance
event_bus = EventBus()


async def sse_event_generator(q: asyncio.Queue) -> AsyncGenerator[str, None]:
    """Yield SSE formatted messages to the client."""
    try:
        # Send initial keepalive / connection confirmed
        yield f"event: connected\ndata: {json.dumps({'status': 'stream_active'})}\n\n"
        while True:
            try:
                # Wait for next event with a 20s heartbeat keepalive
                msg = await asyncio.wait_for(q.get(), timeout=20.0)
                event_name = msg.get("type", "message")
                data_str = json.dumps(msg.get("data", {}))
                yield f"event: {event_name}\ndata: {data_str}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        event_bus.unsubscribe(q)
