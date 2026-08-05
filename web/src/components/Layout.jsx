import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Sun, Moon, Plus } from 'lucide-react';
import Sidebar from './Sidebar';

function useTheme() {
  const [isDark, setIsDark] = useState(false);

  const read = () => {
    const set = document.documentElement.dataset.theme;
    const system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    setIsDark((set || system) === 'dark');
  };

  useEffect(() => {
    read();
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener('change', read);
    return () => mq.removeEventListener('change', read);
  }, []);

  const toggle = () => {
    const next = isDark ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('mkt_theme', next); } catch { /* chế độ ẩn danh */ }
    setIsDark(next === 'dark');
  };

  return { isDark, toggle };
}

export default function Layout({ children, phase, phases, onReset, showCampaignNav = true }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { isDark, toggle } = useTheme();
  const isKnowledge = location.pathname.startsWith('/knowledge');

  const startNew = () => { if (onReset) onReset(); navigate('/'); };

  return (
    <div className="min-h-screen md:h-screen md:overflow-hidden flex flex-col md:flex-row">
      {/* Rail điều hướng — giữ im lặng để nội dung nổi lên */}
      <aside className="shrink-0 w-full md:w-[264px] flex md:flex-col border-b md:border-b-0 md:border-r border-rule">
        <div className="flex md:block items-center justify-between w-full px-5 py-4 md:px-6 md:py-7">
          <button onClick={() => navigate('/')} className="text-left">
            <div className="font-copy text-[1.0625rem] font-semibold leading-tight text-ink">
              Nhà của Gấu Trắng
            </div>
            <div className="t-label mt-1">Campaign Engine</div>
          </button>

          <div className="flex md:hidden items-center gap-1.5">
            <button onClick={toggle} className="btn btn-quiet !px-2.5" aria-label="Đổi giao diện sáng tối">
              {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <button onClick={() => navigate('/knowledge')} className="btn btn-default !py-2 !px-3 !text-[13px]">
              Kho brand
            </button>
            <button onClick={startNew} className="btn btn-primary !py-2 !px-3 !text-[13px]">
              Mới
            </button>
          </div>
        </div>

        {showCampaignNav && phase && (
          <div className="hidden md:block flex-1 overflow-y-auto px-3">
            <Sidebar phase={phase} phases={phases} />
          </div>
        )}
        {!showCampaignNav && <div className="hidden md:block flex-1" />}

        <div className="hidden md:flex flex-col gap-1.5 p-4 border-t border-rule">
          <button
            onClick={() => navigate('/knowledge')}
            className={`btn w-full !justify-start ${isKnowledge ? 'btn-default' : 'btn-quiet'}`}
          >
            Kho brand
          </button>
          <button onClick={startNew} className="btn btn-primary w-full !justify-start">
            <Plus className="w-4 h-4" /> Chiến dịch mới
          </button>
          <button onClick={toggle} className="btn btn-quiet w-full !justify-start !text-[13px]">
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            {isDark ? 'Giao diện sáng' : 'Giao diện tối'}
          </button>
        </div>
      </aside>

      {/* Cột nội dung — chặn bề rộng để văn xuôi dễ đọc */}
      <main className="flex-1 md:overflow-y-auto">
        <div className="mx-auto w-full max-w-[880px] px-5 py-8 md:px-10 md:py-12 lg:px-12">
          {children}
        </div>
      </main>
    </div>
  );
}
