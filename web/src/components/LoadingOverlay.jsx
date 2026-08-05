import { motion, AnimatePresence } from 'framer-motion';
import { Check, Loader2 } from 'lucide-react';

/**
 * Overlay chờ. Khi có `steps` từ luồng SSE thì hiện đúng việc server đang làm;
 * không có thì lùi về thanh chạy không xác định.
 */
export default function LoadingOverlay({
  show,
  title = 'Đang xử lý',
  description = 'Hệ thống đang làm việc.',
  hint = 'Thường mất 30–60 giây.',
  steps = [],
}) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center px-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: .2 }}
          style={{ background: 'color-mix(in srgb, var(--void) 72%, transparent)', backdropFilter: 'blur(6px)' }}
          role="alertdialog"
          aria-busy="true"
          aria-label={title}
        >
          <motion.div
            className="sheet w-full max-w-md px-7 py-7"
            initial={{ opacity: 0, y: 14, scale: .98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: .99 }}
            transition={{ type: 'spring', stiffness: 320, damping: 30 }}
          >
            <p className="t-section mb-1.5">{title}</p>
            <p className="text-[0.9375rem] text-ink-2 leading-relaxed mb-6">{description}</p>

            {steps.length > 0 ? (
              <ol className="space-y-3 mb-6" aria-live="polite">
                <AnimatePresence initial={false}>
                  {steps.map((step) => (
                    <motion.li
                      key={step.node}
                      layout
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ type: 'spring', stiffness: 400, damping: 34 }}
                      className="flex items-center gap-3"
                    >
                      <span
                        className={`w-[18px] h-[18px] shrink-0 rounded-full flex items-center justify-center ${step.done ? '' : 'breathe'}`}
                        style={
                          step.done
                            ? { background: 'var(--pass-soft)', color: 'var(--pass)',
                                boxShadow: 'inset 0 0 0 1px rgba(159,212,180,.45)' }
                            : { background: 'var(--cham)', color: 'var(--on-cham)' }
                        }
                      >
                        {step.done && <Check className="w-2.5 h-2.5" strokeWidth={3.5} />}
                      </span>
                      <span
                        className="text-[0.875rem] transition-colors"
                        style={{ color: step.done ? 'var(--ink-3)' : 'var(--ink)' }}
                      >
                        {step.message}
                      </span>
                    </motion.li>
                  ))}
                </AnimatePresence>
              </ol>
            ) : (
              <div className="flex items-center gap-3 mb-6">
                <Loader2 className="w-4 h-4 animate-spin" style={{ color: 'var(--cham)' }} />
                <div className="flex-1 h-[3px] overflow-hidden rounded-full" style={{ background: 'rgba(255,255,255,.06)' }}>
                  <div className="sweep h-full w-1/3 rounded-full" style={{ background: 'var(--cham)' }} />
                </div>
              </div>
            )}

            <p className="t-label">{hint}</p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
