import { Check } from 'lucide-react';

/* Đánh số là hợp lệ ở đây: các bước này THẬT SỰ là một trình tự,
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
    <nav className="py-2">
      <ol>
        {phases.map((p, i) => {
          const isActive = p === phase;
          const isDone = i < currentIdx;

          return (
            <li key={p}>
              <div
                aria-current={isActive ? 'step' : undefined}
                className={`flex items-center gap-3 py-2.5 pl-3 pr-2 border-l-2 transition-colors ${
                  isActive
                    ? 'border-cham text-ink'
                    : 'border-transparent text-ink-3'
                }`}
              >
                <span
                  className={`w-5 shrink-0 text-center font-data text-[0.75rem] num ${
                    isActive ? 'text-cham' : isDone ? 'text-pass' : 'text-ink-3'
                  }`}
                >
                  {isDone ? <Check className="w-3.5 h-3.5 mx-auto" strokeWidth={2.5} /> : i + 1}
                </span>
                <span className={`text-[0.875rem] ${isActive ? 'font-semibold' : 'font-normal'}`}>
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
