import { useState, useEffect } from 'react';
import { Loader2, KeyRound, AlertTriangle } from 'lucide-react';
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
          ? 'Access key không đúng.'
          : 'Không kết nối được server. Thử lại sau.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (phase === 'authed') return children;

  if (phase === 'checking') {
    return (
      <CenteredCard>
        <Loader2 className="w-6 h-6 animate-spin mx-auto opacity-60" />
      </CenteredCard>
    );
  }

  if (phase === 'misconfigured' || phase === 'offline') {
    const isConfig = phase === 'misconfigured';
    return (
      <CenteredCard>
        <AlertTriangle className="w-8 h-8 mx-auto mb-4 text-amber-400" />
        <h1 className="text-xl font-bold mb-2">
          {isConfig ? 'Server chưa được cấu hình' : 'Không kết nối được server'}
        </h1>
        <p className="text-sm opacity-70 leading-relaxed">
          {isConfig
            ? 'Thiếu biến môi trường APP_API_KEY. Quản trị viên cần set biến này rồi redeploy.'
            : 'Kiểm tra kết nối mạng hoặc trạng thái server rồi tải lại trang.'}
        </p>
      </CenteredCard>
    );
  }

  return (
    <CenteredCard>
      <KeyRound className="w-8 h-8 mx-auto mb-4 text-purple-400" />
      <h1 className="text-2xl font-bold mb-2 tracking-tight">Marketing Campaign Engine</h1>
      <p className="text-sm opacity-60 mb-6">Nhập access key để tiếp tục.</p>

      <form onSubmit={handleSubmit}>
        <input
          type="password"
          value={keyInput}
          onChange={(e) => setKeyInput(e.target.value)}
          placeholder="Access key"
          autoFocus
          autoComplete="current-password"
          className="w-full p-4 rounded-xl text-sm glass-input placeholder:opacity-40 text-center tracking-wider"
        />

        {error && (
          <p className="text-sm text-red-400 mt-3 animate-in fade-in">{error}</p>
        )}

        <button
          type="submit"
          disabled={submitting || !keyInput.trim()}
          className="w-full mt-5 py-4 rounded-xl text-base font-bold flex items-center justify-center gap-2 btn-primary disabled:opacity-40"
        >
          {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
          {submitting ? 'Đang kiểm tra...' : 'Vào ứng dụng'}
        </button>
      </form>
    </CenteredCard>
  );
}

function CenteredCard({ children }) {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="glass-panel p-8 md:p-10 rounded-2xl w-full max-w-md text-center animate-in fade-in slide-in-from-bottom-4 duration-500">
        {children}
      </div>
    </div>
  );
}
