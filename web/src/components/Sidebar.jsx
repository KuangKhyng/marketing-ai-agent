import { Check, Circle, Loader2 } from 'lucide-react';

const PHASE_CONFIG = {
  input:           { label: 'Campaign Brief',   icon: '📝' },
  brief_review:    { label: 'Brief Review',     icon: '📋' },
  strategy_review: { label: 'Strategy Review',  icon: '🎯' },
  content_review:  { label: 'Content Review',   icon: '✍️' },
  final_review:    { label: 'Final Review',     icon: '📊' },
  export:          { label: 'Export',            icon: '📦' },
};

export default function Sidebar({ phase, phases }) {
  const currentIdx = phases.indexOf(phase);

  return (
    <nav className="flex-1 px-2 space-y-2">
      {phases.map((p, i) => {
        const config = PHASE_CONFIG[p];
        const isActive = p === phase;
        const isDone = i < currentIdx;

        return (
          <div key={p} className={`flex items-center gap-3 py-3 px-4 rounded-xl transition-all duration-300 ${
                 isActive ? 'bg-gradient-to-r from-purple-500/20 to-transparent border border-purple-500/30 text-white shadow-[0_0_15px_rgba(139,92,246,0.1)]' : 
                 isDone ? 'text-emerald-400' : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
               }`}>
            <span className={`text-base w-6 text-center flex items-center justify-center ${isActive ? 'scale-110 drop-shadow-md' : ''}`}>
              {isDone ? '✓' : config.icon}
            </span>
            <span className={`text-sm tracking-wide ${isActive ? 'font-semibold text-purple-200' : 'font-medium'}`}>
              {config.label}
            </span>
          </div>
        );
      })}
    </nav>
  );
}
