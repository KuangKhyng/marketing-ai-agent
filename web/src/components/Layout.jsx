import Sidebar from './Sidebar';

export default function Layout({ children, phase, phases, onReset }) {
  return (
    <div className="flex h-screen w-full overflow-hidden">
      {/* Sidebar - Glass panel without blur on the side if bg is already global */}
      <aside className="w-72 flex flex-col glass-panel border-y-0 border-l-0 border-r border-[#2d2d4a]/50">
        <div className="p-8 pb-4">
          <h1 className="text-2xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-pink-500">
            ✦ Marketing AI
          </h1>
          <p className="text-sm mt-2 opacity-70 tracking-wide uppercase font-medium">
            Campaign Engine
          </p>
        </div>
        <div className="px-4 py-6 flex-1 overflow-y-auto">
          <Sidebar phase={phase} phases={phases} />
        </div>
        <div className="mt-auto p-6">
          <button onClick={onReset}
                  className="w-full py-3 rounded-xl text-sm font-semibold transition-all btn-secondary flex items-center justify-center gap-2">
            <span>✨</span> New Campaign
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-10 lg:p-14">
        <div className="max-w-4xl mx-auto w-full">
          {children}
        </div>
      </main>
    </div>
  );
}
