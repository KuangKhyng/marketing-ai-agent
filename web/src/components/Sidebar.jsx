import { Check } from 'lucide-react';

/* Đánh số hợp lệ ở đây: các bước này thật sự là một trình tự,
   thứ tự mang thông tin người dùng cần. */
const PHASE_LABEL = {
  input:           'Đề bài',
  brief_review:    'Duyệt brief',
  strategy_review: 'Duyệt chiến lược',
  content_review:  'Duyệt nội dung',
  final_review:    'Chấm chất lượng',
  export:          'Bàn giao',
};

export default function Sidebar({ phase, phases }) {
  const currentIdx = phases.indexOf(phase);

  return (
    <nav className="py-3">
      <ol className="relative">
        {/* Đường nối dọc chạy suốt chuỗi bước */}
        <span
          aria-hidden="true"
          className="absolute left-[11px] top-4 bottom-4 w-px"
          style={{ background: 'var(--rule)' }}
        />

        {phases.map((p, i) => {
          const isActive = p === phase;
          const isDone = i < currentIdx;

          return (
            <li key={p} className="relative">
              <div
                aria-current={isActive ? 'step' : undefined}
                className="flex items-center gap-3 py-2.5 pl-0 pr-2 rounded-[10px] transition-colors"
                style={isActive ? { background: 'rgba(255,255,255,.04)' } : undefined}
              >
                <span
                  className="relative z-10 w-[23px] h-[23px] shrink-0 rounded-full flex items-center justify-center
                             font-data text-[0.6875rem] num transition-colors"
                  style={
                    isActive
                      ? { background: 'var(--cham)', color: 'var(--on-cham)', fontWeight: 600,
                          boxShadow: '0 0 16px rgba(227,179,65,.45)' }
                      : isDone
                        ? { background: 'var(--pass-soft)', color: 'var(--pass)',
                            boxShadow: 'inset 0 0 0 1px rgba(95,212,155,.4)' }
                        : { background: 'var(--paper)', color: 'var(--ink-3)',
                            boxShadow: 'inset 0 0 0 1px var(--rule)' }
                  }
                >
                  {isDone ? <Check className="w-3 h-3" strokeWidth={3} /> : i + 1}
                </span>

                <span
                  className="text-[0.875rem] transition-colors"
                  style={{
                    color: isActive ? 'var(--ink)' : isDone ? 'var(--ink-2)' : 'var(--ink-3)',
                    fontWeight: isActive ? 500 : 400,
                  }}
                >
                  {PHASE_LABEL[p] || p}
                </span>
              </div>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
