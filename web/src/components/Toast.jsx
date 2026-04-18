import { useState, useEffect } from 'react';

export function useToast() {
  const [toast, setToast] = useState(null);

  const show = (message, type = 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  const Toast = () => {
    if (!toast) return null;
    
    return (
      <div className={`fixed bottom-6 right-6 z-50 px-6 py-3 rounded-xl text-sm font-medium shadow-2xl animate-in slide-in-from-bottom-4 ${
        toast.type === 'error' ? 'bg-red-500/90 text-white' :
        toast.type === 'success' ? 'bg-emerald-500/90 text-white' :
        'bg-purple-500/90 text-white'
      }`}>
        {toast.message}
      </div>
    );
  };

  return { showToast: show, Toast };
}
