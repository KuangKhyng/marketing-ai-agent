export default function LoadingOverlay({
  show,
  title = 'Đang xử lý',
  description = 'AI đang làm việc.',
  hint = 'Thường mất 30–60 giây.',
}) {
  if (!show) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-6"
      style={{ background: 'color-mix(in srgb, var(--paper) 78%, transparent)' }}
      role="alertdialog"
      aria-busy="true"
      aria-label={title}
    >
      <div className="sheet w-full max-w-sm px-6 py-6" style={{ boxShadow: '0 10px 34px rgba(0,0,0,.10)' }}>
        <p className="t-section mb-1.5">{title}</p>
        <p className="text-[0.875rem] text-ink-2 leading-relaxed mb-5">{description}</p>

        {/* Thanh tiến trình không xác định — không giả vờ biết còn bao lâu */}
        <div className="h-[3px] w-full overflow-hidden" style={{ background: 'var(--inset)' }}>
          <div className="h-full w-1/3 bar-slide" style={{ background: 'var(--cham)' }} />
        </div>

        <p className="t-label mt-4">{hint}</p>
      </div>

      <style>{`
        @keyframes bar-slide {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(300%); }
        }
        .bar-slide { animation: bar-slide 1.4s ease-in-out infinite; }
        @media (prefers-reduced-motion: reduce) {
          .bar-slide { animation: none; width: 100%; }
        }
      `}</style>
    </div>
  );
}
