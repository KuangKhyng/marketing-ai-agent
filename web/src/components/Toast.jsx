import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, AlertCircle, Info } from 'lucide-react';

const ICONS = { success: Check, error: AlertCircle, info: Info };

export function useToast() {
  const [toast, setToast] = useState(null);

  const show = (message, type = 'error') => {
    setToast({ message, type, id: Date.now() });
    setTimeout(() => setToast(null), 5000);
  };

  const Toast = () => {
    const accent =
      toast?.type === 'success' ? 'var(--pass)' :
      toast?.type === 'error'   ? 'var(--fail)' : 'var(--cham)';
    const Icon = ICONS[toast?.type] || Info;

    return (
      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast.id}
            role="status"
            aria-live="polite"
            className="sheet fixed bottom-6 right-6 z-50 max-w-sm flex items-start gap-3 pl-4 pr-5 py-3.5"
            initial={{ opacity: 0, y: 20, scale: .96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: .98 }}
            transition={{ type: 'spring', stiffness: 380, damping: 28 }}
          >
            <span
              className="w-5 h-5 shrink-0 rounded-full flex items-center justify-center mt-px"
              style={{ background: `color-mix(in srgb, ${accent} 16%, transparent)`, color: accent }}
            >
              <Icon className="w-3 h-3" strokeWidth={3} />
            </span>
            <span className="text-[0.875rem] leading-snug">{toast.message}</span>
          </motion.div>
        )}
      </AnimatePresence>
    );
  };

  return { showToast: show, Toast };
}
