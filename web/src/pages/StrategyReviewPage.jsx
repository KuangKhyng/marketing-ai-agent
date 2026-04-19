import { useState } from 'react';
import { campaignAPI } from '../api/client';
import { Check, RotateCcw, Loader2, ArrowLeft } from 'lucide-react';

const FEEDBACK_OPTIONS = [
  { key: 'tone', label: 'Tone chưa phù hợp' },
  { key: 'angle', label: 'Góc tiếp cận chưa đúng' },
  { key: 'audience', label: 'Chưa hiểu đúng audience' },
  { key: 'hook', label: 'Hook chưa đủ mạnh' },
  { key: 'cta', label: 'CTA chưa rõ ràng' },
  { key: 'platform', label: 'Platform approach chưa đúng' },
];

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useToast } from '../components/Toast';
import LoadingOverlay from '../components/LoadingOverlay';

export default function StrategyReviewPage({ campaignData, setCampaignData, setPhase, loading, setLoading }) {
  const { showToast, Toast } = useToast();
  const [checks, setChecks] = useState([]);
  const [comment, setComment] = useState('');

  const handleApprove = async () => {
    setLoading(true);
    try {
      const { data } = await campaignAPI.reviewStrategy(campaignData.run_id, {
        approved: true,
        feedback_checks: [],
        comment: null,
      });
      setCampaignData(data);
      setPhase('content_review');
    } catch(err) {
      showToast('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleRevise = async () => {
    if (checks.length === 0 && !comment) {
      showToast('Vui lòng chọn ít nhất 1 vấn đề hoặc viết comment.');
      return;
    }
    setLoading(true);
    try {
      const { data } = await campaignAPI.reviewStrategy(campaignData.run_id, {
        approved: false,
        feedback_checks: checks,
        comment,
      });
      setCampaignData(data);
      setComment('');
      setChecks([]);
    } catch(err) {
      showToast('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="mb-8">
        <h2 className="text-4xl font-bold mb-3 tracking-tight">Strategy Review</h2>
        <p className="text-lg opacity-70">
          Xem lại chiến lược campaign trước khi tạo content chi tiết.
        </p>
      </div>

      {/* Strategy content */}
      <div className="glass-panel rounded-2xl p-8 mb-8 text-white/90 shadow-xl relative overflow-hidden prose prose-invert prose-sm max-w-none">
        <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 left-0 w-40 h-40 bg-blue-500/10 rounded-full blur-3xl"></div>
        <div className="relative z-10">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {campaignData?.strategy || ''}
          </ReactMarkdown>
        </div>
      </div>

      {campaignData?.revision_count > 0 && (
          <p className="text-sm font-semibold text-yellow-400 mb-6 bg-yellow-400/10 inline-block px-4 py-2 rounded-lg border border-yellow-400/20">
             Đã chỉnh sửa (Revision): {campaignData.revision_count}/3
          </p>
      )}

      {/* Feedback section */}
      <div className="glass-panel rounded-2xl p-8 mb-8">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2 text-yellow-400">
          <span>💡</span> Feedback (Nếu cần AI điều chỉnh lại)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
          {FEEDBACK_OPTIONS.map(opt => (
            <label key={opt.key}
                   className={`flex items-center gap-3 p-4 rounded-xl cursor-pointer text-sm font-medium transition-all ${
                     checks.includes(opt.key) 
                     ? 'bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/40 text-purple-200 shadow-md' 
                     : 'bg-[#252540]/60 border border-white/5 hover:bg-white/5 text-gray-300'
                   }`}>
              <input type="checkbox" checked={checks.includes(opt.key)}
                     onChange={e => {
                       if (e.target.checked) setChecks([...checks, opt.key]);
                       else setChecks(checks.filter(c => c !== opt.key));
                     }}
                     className="w-4 h-4 rounded text-purple-500 focus:ring-purple-500 bg-[#0f0f1a] border-gray-600" />
              {opt.label}
            </label>
          ))}
        </div>

        <textarea value={comment} onChange={e => setComment(e.target.value)}
                  placeholder="Viết chú thích thêm cho AI (ví dụ: 'Làm nó ngầu hơn một chút', 'Thay đổi CTA thành Inbox page')..."
                  rows={4}
                  className="w-full p-5 rounded-xl text-base glass-input resize-none placeholder:opacity-50"
                  />
      </div>

      {/* Action buttons */}
      <div className="flex gap-4">
        <button onClick={() => setPhase('brief_review')} disabled={loading}
                className="px-6 py-4 rounded-xl text-base font-semibold flex items-center justify-center gap-2 cursor-pointer btn-secondary">
          <ArrowLeft className="w-5 h-5" />
          Brief
        </button>
        <button onClick={handleRevise} disabled={loading || (checks.length === 0 && !comment)}
                className="w-1/3 py-4 rounded-xl text-base font-semibold flex items-center justify-center gap-2 cursor-pointer btn-secondary disabled:opacity-40">
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <RotateCcw className="w-5 h-5" />}
          Yêu cầu sửa
        </button>
        <button onClick={handleApprove} disabled={loading}
                className="flex-1 py-4 rounded-xl text-base font-semibold flex items-center justify-center gap-2 cursor-pointer bg-emerald-500 hover:bg-emerald-400 text-white shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all">
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5 text-white" />}
          Approve — Tạo Content
        </button>
      </div>

      <LoadingOverlay
        show={loading}
        title={checks.length === 0 && !comment ? 'Đang tạo content...' : 'Đang điều chỉnh strategy...'}
        description={checks.length === 0 && !comment
          ? 'AI đang thiết kế nội dung chi tiết cho các kênh.'
          : 'AI đang sửa chiến lược theo feedback của bạn.'}
      />

      <Toast />
    </div>
  );
}
