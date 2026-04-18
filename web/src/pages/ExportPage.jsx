import { useState } from 'react';
import { campaignAPI } from '../api/client';
import { Download, FileText, Code2, Sparkles, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';

function formatPieceForCopy(piece) {
  const parts = [];
  if (piece.hook) parts.push(piece.hook);
  parts.push(piece.body);
  if (piece.cta_text) parts.push(`\n${piece.cta_text}`);
  if (piece.hashtags?.length > 0) {
    parts.push(`\n${piece.hashtags.join(' ')}`);
  }
  return parts.join('\n\n');
}

function CopyButton({ text, label }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <button onClick={handleCopy}
            className={`px-4 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-all cursor-pointer border ${
              copied 
                ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400' 
                : 'bg-white/5 border-white/10 hover:border-purple-500/40 hover:bg-purple-500/10 text-gray-300'
            }`}>
      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
      {copied ? 'Đã copy!' : label}
    </button>
  );
}

const CHANNEL_ICONS = {
  facebook: '📘',
  instagram: '📸',
  tiktok: '🎵',
};

export default function ExportPage({ campaignData, setPhase }) {
  const [downloading, setDownloading] = useState(false);
  const [expandedPiece, setExpandedPiece] = useState(null);

  if (!campaignData) return null;
  const runId = campaignData.run_id;
  const pieces = campaignData?.content?.pieces || [];

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
    <div className="animate-in zoom-in-95 duration-1000 flex flex-col items-center">
      <div className="w-32 h-32 bg-gradient-to-tr from-purple-500 to-emerald-400 rounded-full blur-3xl absolute opacity-20 animate-pulse"></div>
      
      <div className="bg-emerald-500/20 w-24 h-24 rounded-full flex items-center justify-center mb-8 border border-emerald-500/40 relative z-10 shadow-[0_0_50px_rgba(16,185,129,0.3)]">
        <Sparkles className="w-12 h-12 text-emerald-400" />
      </div>

      <h2 className="text-5xl font-black mb-4 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-teal-400 relative z-10">
        Campaign Ready!
      </h2>
      <p className="text-xl mb-8 opacity-80 relative z-10 max-w-lg text-center">
        Chiến dịch đã sẵn sàng. Copy trực tiếp hoặc download assets.
      </p>

      {/* Stats */}
      <div className="flex justify-center gap-6 mb-8 relative z-10 w-full max-w-2xl">
        <div className="glass-panel p-6 rounded-2xl flex-1 border-t-2 border-t-purple-500/50">
          <p className="text-xs font-bold uppercase tracking-wider mb-2 opacity-60">Run ID</p>
          <p className="font-mono text-xl tracking-wider">{runId.slice(0, 8)}</p>
        </div>
        <div className="glass-panel p-6 rounded-2xl flex-1 border-t-2 border-t-yellow-400/50">
          <p className="text-xs font-bold uppercase tracking-wider mb-2 opacity-60">Cost Estimate</p>
          <p className="font-mono font-bold text-3xl text-yellow-400">${campaignData.cost_estimate?.toFixed(3)}</p>
        </div>
      </div>

      {/* Smart Copy Section */}
      {pieces.length > 0 && (
        <div className="w-full max-w-2xl relative z-10 mb-10">
          <h3 className="text-lg font-bold mb-4 uppercase tracking-widest text-purple-300">📋 Smart Copy</h3>
          <div className="space-y-3">
            {pieces.map((piece, i) => {
              const copyText = formatPieceForCopy(piece);
              const icon = CHANNEL_ICONS[piece.channel] || '📄';
              const isExpanded = expandedPiece === i;
              return (
                <div key={i} className="glass-panel rounded-2xl overflow-hidden">
                  <div className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{icon}</span>
                      <div>
                        <p className="font-semibold text-sm">
                          {piece.channel.toUpperCase()} — {piece.deliverable.replace('_', ' ')}
                        </p>
                        <p className="text-xs opacity-50">{piece.word_count} words</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <CopyButton text={copyText} label="Copy" />
                      <button onClick={() => setExpandedPiece(isExpanded ? null : i)}
                              className="p-2 rounded-lg hover:bg-white/10 transition-colors">
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                  {isExpanded && (
                    <div className="px-4 pb-4 animate-in fade-in slide-in-from-top-2 duration-300">
                      <div className="p-4 rounded-xl bg-[#0f0f1a]/60 border border-white/5 text-sm whitespace-pre-wrap leading-relaxed text-gray-300 max-h-60 overflow-y-auto">
                        {copyText}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          {/* Copy All */}
          <div className="mt-3">
            <CopyButton 
              text={pieces.map(p => `=== ${p.channel.toUpperCase()} — ${p.deliverable} ===\n\n${formatPieceForCopy(p)}`).join('\n\n---\n\n')} 
              label="📋 Copy All Pieces" 
            />
          </div>
        </div>
      )}

      {/* Download Section */}
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
