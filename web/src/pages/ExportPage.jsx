import { useState } from 'react';
import { campaignAPI } from '../api/client';
import { Download, FileText, Code2, Sparkles } from 'lucide-react';

export default function ExportPage({ campaignData, setPhase }) {
  const [downloading, setDownloading] = useState(false);

  if (!campaignData) return null;
  const runId = campaignData.run_id;

  const handleDownload = async (format) => {
    setDownloading(true);
    try {
      const response = await campaignAPI.download(runId, format);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `campaign-${runId}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (err) {
      alert("Error downloading file.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="animate-in zoom-in-95 duration-1000 text-center py-16 flex flex-col items-center justify-center h-full">
      <div className="w-32 h-32 bg-gradient-to-tr from-purple-500 to-emerald-400 rounded-full blur-3xl absolute opacity-20 animate-pulse"></div>
      
      <div className="bg-emerald-500/20 w-24 h-24 rounded-full flex items-center justify-center mb-8 border border-emerald-500/40 relative z-10 shadow-[0_0_50px_rgba(16,185,129,0.3)]">
        <Sparkles className="w-12 h-12 text-emerald-400" />
      </div>

      <h2 className="text-5xl font-black mb-4 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-teal-400 relative z-10">
        Campaign Ready!
      </h2>
      <p className="text-xl mb-12 opacity-80 relative z-10 max-w-lg">
        Chiến dịch của bạn đã được đóng gói thành công. Dữ liệu đã sẵn sàng để publish.
      </p>

      <div className="flex justify-center gap-6 mb-12 relative z-10 w-full max-w-2xl">
        <div className="glass-panel p-6 rounded-2xl flex-1 border-t-2 border-t-purple-500/50">
          <p className="text-xs font-bold uppercase tracking-wider mb-2 opacity-60">Run ID</p>
          <p className="font-mono text-xl tracking-wider">{runId.slice(0, 8)}</p>
        </div>
        <div className="glass-panel p-6 rounded-2xl flex-1 border-t-2 border-t-yellow-400/50">
          <p className="text-xs font-bold uppercase tracking-wider mb-2 opacity-60">Cost Estimate</p>
          <p className="font-mono font-bold text-3xl text-yellow-400">${campaignData.cost_estimate?.toFixed(3)}</p>
        </div>
      </div>

      <h3 className="text-lg font-bold mb-6 uppercase tracking-widest text-purple-300 relative z-10">📥 Download Assets</h3>
      <div className="flex justify-center gap-4 relative z-10">
        <button onClick={() => handleDownload('md')} disabled={downloading}
                className="px-8 py-4 rounded-xl text-base font-bold cursor-pointer transition-all hover:-translate-y-1 hover:shadow-lg hover:shadow-purple-500/20 bg-gradient-to-r from-purple-600 to-indigo-600 border border-purple-500/50 text-white flex items-center gap-2">
          <FileText className="w-5 h-5"/>
          Markdown (.md)
        </button>
        <button onClick={() => handleDownload('json')} disabled={downloading}
                className="px-8 py-4 rounded-xl text-base font-bold cursor-pointer transition-all hover:-translate-y-1 hover:shadow-lg glass-panel flex items-center gap-2 text-white/90">
          <Code2 className="w-5 h-5" />
          JSON Payload
        </button>
      </div>
      
      <button onClick={() => { setPhase('input'); }}
              className="mt-16 text-sm font-semibold opacity-60 hover:opacity-100 transition-opacity border-b border-transparent hover:border-white pb-1 relative z-10 cursor-pointer">
        + Bắt đầu Campaign mới
      </button>
    </div>
  );
}
