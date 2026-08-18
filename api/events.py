"""
ProgressBus — cầu nối event từ worker thread sang SSE stream.

Hai điểm khác bản trước, đều là lỗi thật:

1. Dùng asyncio.Queue chứ không phải queue.Queue.
   Bản trước SSE endpoint chờ event bằng `run_in_executor(q.get(timeout=1))`
   trong vòng lặp vô hạn, nên MỖI kết nối SSE chiếm cứng một thread của
   threadpool AnyIO. Các endpoint phase đều là `def` (sync) nên dùng chung
   threadpool đó — vài chục người xem tiến trình là hết thread để chạy
   pipeline. Giờ SSE chỉ `await`, không tốn thread nào.

2. Nhiều subscriber cho cùng một run_id.
   Bản trước `create()` ghi đè queue cũ trong dict: mở tab thứ hai là tab đầu
   không bao giờ nhận sentinel nữa và treo vô hạn. Giờ mỗi subscriber có queue
   riêng, event fan-out cho tất cả, đóng thì đóng hết.

Producer (worker thread) gọi push/close; chúng đẩy vào event loop bằng
call_soon_threadsafe vì asyncio.Queue không thread-safe.
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Chặn một run phát quá nhiều event làm phình bộ nhớ nếu client đọc chậm
_MAX_QUEUED = 100


class _Subscription:
    """Một kết nối SSE đang mở."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=_MAX_QUEUED)


class ProgressBus:
    def __init__(self):
        # run_id -> danh sách subscriber (thường 1, có thể nhiều nếu mở 2 tab)
        self._subs: dict[str, list[_Subscription]] = {}

    def subscribe(self, run_id: str) -> _Subscription:
        """Gọi từ SSE endpoint (async). Trả về subscription để đọc event."""
        sub = _Subscription(asyncio.get_running_loop())
        self._subs.setdefault(run_id, []).append(sub)
        return sub

    def unsubscribe(self, run_id: str, sub: _Subscription) -> None:
        """Client ngắt kết nối — bỏ subscription, không ảnh hưởng tab khác."""
        subs = self._subs.get(run_id)
        if not subs:
            return
        if sub in subs:
            subs.remove(sub)
        if not subs:
            self._subs.pop(run_id, None)

    def _deliver(self, run_id: str, item) -> None:
        """Đẩy item vào queue của mọi subscriber. Gọi được từ thread khác."""
        for sub in list(self._subs.get(run_id, [])):
            def put(q=sub.queue, value=item):
                try:
                    q.put_nowait(value)
                except asyncio.QueueFull:
                    # Client đọc quá chậm — bỏ event tiến trình, không sao,
                    # nhưng phải ghi lại để biết mà điều tra.
                    logger.warning("Bỏ event tiến trình của run %s: queue đầy", run_id)

            try:
                sub.loop.call_soon_threadsafe(put)
            except RuntimeError:
                # Event loop đã đóng — client đi rồi
                pass

    def push(self, run_id: str, event: dict) -> None:
        """Phát một event. Không có ai lắng nghe thì bỏ qua."""
        self._deliver(run_id, event)

    def close(self, run_id: str) -> None:
        """Báo cho mọi stream của run này là đã xong (None = sentinel)."""
        self._deliver(run_id, None)

    def subscriber_count(self, run_id: str) -> int:
        return len(self._subs.get(run_id, []))


progress_bus = ProgressBus()
