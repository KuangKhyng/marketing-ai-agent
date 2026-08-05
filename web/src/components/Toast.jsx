import { useState } from 'react';

export function useToast() {
  const [toast, setToast] = useState(null);

  const show = (message, type = 'error') => {
    setToast({ message, type, id: Date.now() });
    setTimeout(() => setToast(null), 5000);
  };

  const Toast = () => {
    if (!toast) return null;

    const accent =
      toast.type === 'success' ? 'var(--pass)' :
      toast.type === 'error'   ? 'var(--fail)' : 'var(--cham)';

    return (
      <div
        role="status"
        aria-live="polite"
        className="rise fixed bottom-5 right-5 z-50 max-w-sm sheet px-4 py-3 text-[0.875rem] leading-snug"
        style={{ borderLeft: `2px solid ${accent}`, boxShadow: '0 6px 20px rgba(0,0,0,.09)' }}
      >
        {toast.message}
      </div>
    );
  };

  return { showToast: show, Toast };
}
