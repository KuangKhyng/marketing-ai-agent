"""
ProgressBus — thread-safe event queue for SSE streaming.

Phase handlers (sync, run in FastAPI threadpool) push events here.
SSE endpoint (async) reads events and streams to client.

Usage:
    # In SSE endpoint (async):
    q = progress_bus.create(run_id)
    # In phase handler (sync, threadpool):
    progress_bus.push(run_id, {"type": "node_start", "node": "strategist", ...})
    progress_bus.close(run_id)
"""
import queue
from typing import Optional


class ProgressBus:
    def __init__(self):
        self._queues: dict[str, queue.Queue] = {}

    def create(self, run_id: str) -> queue.Queue:
        """Create a fresh queue for a run. Called by SSE endpoint before phase starts."""
        q: queue.Queue = queue.Queue(maxsize=100)
        self._queues[run_id] = q
        return q

    def push(self, run_id: str, event: dict) -> None:
        """Push an event. No-op if no SSE client is connected for this run_id."""
        q = self._queues.get(run_id)
        if q:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass

    def close(self, run_id: str) -> None:
        """Signal the SSE stream to close (None = sentinel)."""
        q = self._queues.get(run_id)
        if q:
            try:
                q.put_nowait(None)
            except queue.Full:
                pass
        self._queues.pop(run_id, None)

    def get_queue(self, run_id: str) -> Optional[queue.Queue]:
        return self._queues.get(run_id)


progress_bus = ProgressBus()
