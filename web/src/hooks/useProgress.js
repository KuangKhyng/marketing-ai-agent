import { useState, useRef, useCallback } from 'react';
import { streamProgress } from '../api/client';

/**
 * Theo dõi tiến trình dây chuyền theo thời gian thực.
 *
 * Cách dùng:
 *   const { steps, start, stop } = useProgress();
 *   await start(runId);        // phải mở luồng TRƯỚC khi gọi API
 *   try { await campaignAPI.x() } finally { stop() }
 *
 * Nếu SSE hỏng thì chỉ mất phần hiển thị tiến trình, thao tác chính vẫn chạy.
 */
export function useProgress() {
  const [steps, setSteps] = useState([]);
  const abortRef = useRef(null);

  const start = useCallback(async (runId) => {
    abortRef.current?.abort();
    setSteps([]);

    const controller = new AbortController();
    abortRef.current = controller;

    const onEvent = (event) => {
      if (event.type === 'node_start') {
        setSteps(prev =>
          prev.some(s => s.node === event.node)
            ? prev
            : [...prev, { node: event.node, message: event.message, done: false }]
        );
      } else if (event.type === 'node_done') {
        setSteps(prev => prev.map(s => (s.node === event.node ? { ...s, done: true } : s)));
      } else if (event.type === 'cache_hit') {
        setSteps(prev => [...prev, { node: event.node, message: event.message, done: true }]);
      }
    };

    try {
      await streamProgress(runId, onEvent, controller.signal);
    } catch {
      // Không mở được luồng — bỏ qua, overlay lùi về trạng thái không xác định
    }
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setSteps([]);
  }, []);

  return { steps, start, stop };
}
