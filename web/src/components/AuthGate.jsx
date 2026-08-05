import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { authAPI, getAccessKey, setAccessKey, clearAccessKey } from '../api/client';

/**
 * Chặn toàn bộ app cho tới khi có access key hợp lệ.
 *
 * - Server tắt auth (dev)        → render thẳng children
 * - Đã có key hợp lệ trong store → render children
 * - Còn lại                      → hiện form nhập key
 */
export default function AuthGate({ children }) {
  const [phase, setPhase] = useState('checking'); // checking | login | authed | misconfigured | offline
  const [keyInput, setKeyInput] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const { data } = await authAPI.status();
        if (cancelled) return;

        if (data.misconfigured) return setPhase('misconfigured');
        if (!data.auth_required) return setPhase('authed');

        const stored = getAccessKey();
        if (!stored) return setPhase('login');

        try {
          await authAPI.verify(stored);
          if (!cancelled) setPhase('authed');
        } catch {
          clearAccessKey();
          if (!cancelled) setPhase('login');
        }
      } catch {
        if (!cancelled) setPhase('offline');
      }
    })();

    return () => { cancelled = true; };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const key = keyInput.trim();
    if (!key) return;

    setSubmitting(true);
    setError('');
    try {
      await authAPI.verify(key);
      setAccessKey(key);
      setPhase('authed');
    } catch (err) {
      setError(
        err.response?.status === 401
          ? 'Key không đúng. Kiểm tra lại hoặc hỏi người cấp key.'
          : 'Không gọi được server. Thử lại sau ít phút.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (phase === 'authed') return children;

  if (phase === 'checking') {
    return (
      <Frame>
        <Loader2 className="w-5 h-5 animate-spin text-ink-3" />
      </Frame>
    );
  }

  if (phase === 'misconfigured' || phase === 'offline') {
    const isConfig = phase === 'misconfigured';
    return (
      <Frame>
        <div className="max-w-sm">
          <p className="t-label mb-3" style={{ color: 'var(--fail)' }}>
            {isConfig ? 'Cấu hình' : 'Kết nối'}
          </p>
          <h1 className="t-section mb-2">
            {isConfig ? 'Server chưa được cấu hình' : 'Không kết nối được server'}
          </h1>
          <p className="text-[0.9375rem] text-ink-2 leading-relaxed">
            {isConfig
              ? 'Thiếu biến môi trường APP_API_KEY. Quản trị viên cần đặt biến này rồi deploy lại.'
              : 'Kiểm tra kết nối mạng hoặc trạng thái server, sau đó tải lại trang.'}
          </p>
        </div>
      </Frame>
    );
  }

  return (
    <Frame>
      <form onSubmit={handleSubmit} className="w-full max-w-[340px]">
        <div className="font-copy text-[1.375rem] font-semibold leading-tight">
          Campaign Engine
        </div>
        <div className="t-label mt-1.5 mb-7">Nội dung đa kênh</div>

        <label htmlFor="access-key" className="t-label block mb-2">Access key</label>
        <input
          id="access-key"
          type="password"
          value={keyInput}
          onChange={(e) => setKeyInput(e.target.value)}
          autoFocus
          autoComplete="current-password"
          className="field font-data"
          aria-describedby={error ? 'access-key-error' : undefined}
          aria-invalid={error ? 'true' : undefined}
        />

        {error && (
          <p id="access-key-error" className="mt-2.5 text-[0.8125rem] leading-snug" style={{ color: 'var(--fail)' }}>
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting || !keyInput.trim()}
          className="btn btn-primary w-full mt-5"
        >
          {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
          {submitting ? 'Đang kiểm tra' : 'Vào ứng dụng'}
        </button>
      </form>
    </Frame>
  );
}

function Frame({ children }) {
  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="rise">{children}</div>
    </div>
  );
}
