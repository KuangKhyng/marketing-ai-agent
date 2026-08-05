import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Plus } from 'lucide-react';
import Sidebar from './Sidebar';
import Scene from './Scene';

/* Đèn rọi theo con trỏ: một listener duy nhất cho mọi phần tử .spot,
   ghi toạ độ tương đối vào biến CSS. Không state, không re-render. */
function useSpotlight() {
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const onMove = (e) => {
      const el = e.target.closest?.('.spot');
      if (!el) return;
      const r = el.getBoundingClientRect();
      el.style.setProperty('--mx', `${e.clientX - r.left}px`);
      el.style.setProperty('--my', `${e.clientY - r.top}px`);
    };

    window.addEventListener('pointermove', onMove, { passive: true });
    return () => window.removeEventListener('pointermove', onMove);
  }, []);
}

export default function Layout({ children, phase, phases, onReset, showCampaignNav = true }) {
  const navigate = useNavigate();
  const location = useLocation();
  const isKnowledge = location.pathname.startsWith('/knowledge');
  useSpotlight();

  const startNew = () => { if (onReset) onReset(); navigate('/'); };

  return (
    <div className="min-h-screen md:h-screen md:overflow-hidden flex flex-col md:flex-row">
      <Scene intensity={isKnowledge ? 0.28 : 1} />
      <aside className="relative z-10 shrink-0 w-full md:w-[268px] flex md:flex-col md:h-[calc(100vh-2rem)] md:m-4 md:mr-0
                        sheet !rounded-[18px] overflow-hidden">
        <div className="flex md:block items-center justify-between w-full px-5 py-4 md:px-7 md:py-8">
          <button onClick={() => navigate('/')} className="text-left group">
            <div className="flex items-center gap-2.5">
              <span aria-hidden="true" className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ background: 'var(--cham)', boxShadow: '0 0 12px var(--cham-glow)' }} />
              <span className="text-[1.0625rem] font-light tracking-tight"
                    style={{ fontFamily: 'var(--font-display)' }}>
                Nhà của Gấu Trắng
              </span>
            </div>
            <div className="t-label mt-2 md:ml-4">Campaign Engine</div>
          </button>

          <div className="flex md:hidden items-center gap-1.5">
            <button onClick={() => navigate('/knowledge')} className="btn btn-default !py-2 !px-3.5 !text-[13px]">
              Kho brand
            </button>
            <button onClick={startNew} className="btn btn-primary !py-2 !px-3.5 !text-[13px]">
              Mới
            </button>
          </div>
        </div>

        {showCampaignNav && phase && (
          <div className="hidden md:block flex-1 overflow-y-auto px-4">
            <Sidebar phase={phase} phases={phases} />
          </div>
        )}
        {!showCampaignNav && <div className="hidden md:block flex-1" />}

        <div className="hidden md:flex flex-col gap-2 p-5 border-t border-rule">
          <button
            onClick={() => navigate('/knowledge')}
            className={`btn w-full !justify-start ${isKnowledge ? 'btn-default' : 'btn-quiet'}`}
          >
            Kho brand
          </button>
          <button onClick={startNew} className="btn btn-primary w-full !justify-start">
            <Plus className="w-4 h-4" /> Chiến dịch mới
          </button>
        </div>
      </aside>

      <main className="relative z-10 flex-1 md:overflow-y-auto">
        <div className="mx-auto w-full max-w-[880px] px-5 py-9 md:px-10 md:py-12">
          {children}
        </div>
      </main>
    </div>
  );
}
