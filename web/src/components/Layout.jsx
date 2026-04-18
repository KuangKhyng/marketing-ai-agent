import Sidebar from './Sidebar';

export default function Layout({ children, phase, phases, onReset }) {
  return (
    <div className="flex flex-col md:flex-row h-screen w-full overflow-hidden">
      {/* Sidebar / Topbar */}
      <aside className="w-full md:w-72 flex md:flex-col glass-panel border-b md:border-b-0 md:border-r border-[#2d2d4a]/50 shrink-0 items-center md:items-stretch justify-between">
        <div className="p-4 md:p-8 md:pb-4 flex flex-row items-center justify-between w-full md:w-auto">
          <div>
            <h1 className="text-xl md:text-2xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-pink-500">
              ✦ Công chúa Trang
            </h1>
            <p className="text-xs md:text-sm mt-0 md:mt-2 opacity-70 tracking-wide uppercase font-medium hidden md:block">
              Campaign Engine
            </p>
          </div>
          <button onClick={onReset}
                  className="md:hidden px-4 py-2 rounded-xl text-xs font-semibold transition-all btn-secondary flex items-center gap-2">
            <span>✨</span> New
          </button>
        </div>
        <div className="hidden md:flex px-4 py-6 flex-1 overflow-y-auto flex-col w-full">
          <Sidebar phase={phase} phases={phases} />
        </div>
        <div className="hidden md:block mt-auto p-6 w-full">
          <button onClick={onReset}
                  className="w-full py-3 rounded-xl text-sm font-semibold transition-all btn-secondary flex items-center justify-center gap-2">
            <span>✨</span> New Campaign
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-4 md:p-10 lg:p-14">
        <div className="max-w-4xl mx-auto w-full">
          {children}
        </div>
      </main>
    </div>
  );
}
