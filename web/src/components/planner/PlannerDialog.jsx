import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

export default function PlannerDialog({ title, children, onClose, busy = false }) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return <dialog ref={ref} aria-labelledby="planner-dialog-title"
    onCancel={event => { event.preventDefault(); if (!busy) onClose(); }}
    className="planner-dialog w-[min(680px,calc(100vw-2rem))] max-h-[90dvh] overflow-y-auto rounded-2xl border border-rule bg-sheet text-ink p-0">
    <header className="sticky top-0 z-10 bg-sheet border-b border-rule flex justify-between items-center p-5">
      <h2 id="planner-dialog-title" className="text-xl font-medium">{title}</h2>
      <button aria-label="Đóng" disabled={busy} onClick={onClose} className="btn btn-quiet !p-2"><X size={18} /></button>
    </header>
    <fieldset disabled={busy} className="p-5 min-w-0">{children}</fieldset>
  </dialog>;
}
