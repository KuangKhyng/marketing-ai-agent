import { Loader2 } from 'lucide-react';

export default function LoadingOverlay({ show, title = 'Đang xử lý...', description = 'AI đang làm việc, vui lòng chờ.', hint = 'Thường mất khoảng 30-60 giây.' }) {
  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center backdrop-blur-sm">
      <div className="glass-panel p-8 rounded-2xl text-center max-w-sm animate-in zoom-in-95 duration-300">
        <Loader2 className="w-10 h-10 animate-spin text-purple-400 mx-auto mb-4" />
        <p className="text-lg font-semibold mb-2 text-white">{title}</p>
        <p className="text-sm text-gray-400 mb-4">{description}</p>
        <div className="w-full bg-[#0f0f1a] h-2 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 w-full animate-pulse"></div>
        </div>
        <p className="text-xs text-gray-500 mt-4">{hint}</p>
      </div>
    </div>
  );
}
