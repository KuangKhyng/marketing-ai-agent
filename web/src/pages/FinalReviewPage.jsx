import { campaignAPI } from '../api/client';
import { Loader2, ArrowLeft, Download, ShieldCheck } from 'lucide-react';

export default function FinalReviewPage({ campaignData, setCampaignData, setPhase, loading, setLoading }) {
  const result = campaignData?.review_result;

  const handleApprove = async () => {
    setLoading(true);
    try {
      const { data } = await campaignAPI.approveFinal(campaignData.run_id);
      setCampaignData(data);
      setPhase('export');
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setPhase('content_review');
  };

  if (!result) return null;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="mb-8">
        <h2 className="text-4xl font-bold mb-3 tracking-tight flex items-center gap-3">
          <ShieldCheck className="w-10 h-10 text-purple-400" /> AI Review Final
        </h2>
        <p className="text-lg opacity-70">
          Chấm điểm đa chiều (Tone, Factuality, Channel Fit) trước khi chốt hạ.
        </p>
      </div>

      {/* Score cards border gradient trick + glass */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {result.dimension_scores.map(s => (
          <div key={s.dimension} 
               className={`glass-panel p-5 rounded-2xl relative overflow-hidden group transition-all duration-300 hover:-translate-y-1 ${
                 s.passed ? 'hover:shadow-[0_10px_30px_rgba(16,185,129,0.15)]' : 'hover:shadow-[0_10px_30px_rgba(239,68,68,0.15)]'
               }`}>
            <div className={`absolute top-0 left-0 w-full h-1 ${s.passed ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
            <p className="text-xs font-bold tracking-wider mb-2 opacity-60">
              {s.dimension.replace('_', ' ').toUpperCase()}
            </p>
            <div className="flex items-end gap-2 mb-3">
               <p className="text-4xl font-black">{s.score.toFixed(1)}</p>
               <span className="text-lg opacity-50 font-bold mb-1">/10</span>
            </div>
            
            <p className={`text-xs font-bold uppercase tracking-wider mb-3 ${s.passed ? 'text-emerald-400' : 'text-red-400'}`}>
              {s.passed ? '✅ ĐẠT YÊU CẦU' : '❌ CHƯA ĐẠT'}
            </p>
            <p className="text-sm opacity-80 leading-relaxed font-medium line-clamp-3 group-hover:line-clamp-none transition-all">{s.feedback}</p>
          </div>
        ))}
      </div>

      <div className={`glass-panel rounded-2xl p-8 mb-8 text-center border-2 ${result.overall_passed ? 'border-emerald-500/30' : 'border-red-500/30'}`}>
        <h3 className="text-2xl font-bold mb-2">
          Kết quả đánh giá chung: <br className="md:hidden" />
          <span className={`inline-block mt-2 px-6 py-2 rounded-xl ${result.overall_passed ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
            {result.overall_passed ? '🚀 SẴN SÀNG LAUNCH' : '⛔ CẦN SỬA CHỮA'}
          </span>
        </h3>
        {result.revision_instructions && (
             <div className="mt-6 p-6 rounded-xl text-left bg-red-500/10 border border-red-500/20">
                 <p className="font-bold text-red-400 mb-2 flex items-center gap-2"><span>⚠️</span> Gợi ý sửa từ AI:</p>
                 <p className="whitespace-pre-wrap text-sm text-red-100">{result.revision_instructions}</p>
             </div>
        )}
      </div>

      <div className="flex gap-4">
        <button onClick={handleBack} disabled={loading}
                className="w-1/3 py-4 rounded-xl text-base font-semibold flex items-center justify-center gap-2 btn-secondary transition-all">
          <ArrowLeft className="w-5 h-5" />
          Quay lại sửa Content
        </button>
        <button onClick={handleApprove} disabled={loading || !result.overall_passed}
                className="flex-1 py-4 rounded-xl text-base font-semibold flex items-center justify-center gap-2 cursor-pointer btn-primary transition-all disabled:opacity-40">
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Download className="w-5 h-5" />}
          Approve & Export Campaign
        </button>
      </div>
    </div>
  );
}
