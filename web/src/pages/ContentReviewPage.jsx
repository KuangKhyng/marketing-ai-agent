import { useState } from 'react';
import { campaignAPI } from '../api/client';
import { Check, RotateCcw, Loader2, Wand2, Scissors, MessageCircle, Sparkles, ArrowLeft } from 'lucide-react';
import { useToast } from '../components/Toast';
import LoadingOverlay from '../components/LoadingOverlay';

function formatForPlatform(piece) {
  let text = '';
  if (piece.body) text += piece.body;
  if (piece.cta_text) text += '\n\n' + piece.cta_text;
  if (piece.hashtags?.length) {
    text += '\n\n' + piece.hashtags.join(' ');
  }
  return text;
}

const QUICK_ACTIONS = [
  { id: 'rewrite', label: '🔄 Viết lại', icon: RotateCcw, color: 'purple' },
  { id: 'change_hook', label: '🎣 Đổi hook', icon: Sparkles, color: 'yellow' },
  { id: 'shorter', label: '✂️ Ngắn hơn', icon: Scissors, color: 'blue' },
  { id: 'change_tone', label: '🎭 Đổi tone', icon: MessageCircle, color: 'pink' },
];

export default function ContentReviewPage({ campaignData, setCampaignData, setPhase, loading, setLoading }) {
  const { showToast, Toast } = useToast();
  const pieces = campaignData?.content?.pieces || [];
  const [activeTab, setActiveTab] = useState(0);
  const [editMode, setEditMode] = useState({});
  const [edits, setEdits] = useState({});
  const [feedback, setFeedback] = useState({});
  const [quickLoading, setQuickLoading] = useState(null); // action id or null

  const handleApprove = async () => {
    setLoading(true);
    try {
      const pieceFeedbacks = pieces.map((_, i) => ({
        piece_index: i,
        approved: !feedback[i]?.needsChange,
        comment: feedback[i]?.comment || null,
        edited_body: edits[i] || null,
      }));

      const { data } = await campaignAPI.reviewContent(campaignData.run_id, {
        approved: true,
        piece_feedbacks: pieceFeedbacks,
      });
      setCampaignData(data);
      setPhase('final_review');
    } catch(err) {
      showToast('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleRevise = async () => {
    setLoading(true);
    try {
      const pieceFeedbacks = Object.entries(feedback)
        .filter(([_, fb]) => fb.needsChange)
        .map(([i, fb]) => ({
          piece_index: parseInt(i),
          approved: false,
          comment: fb.comment,
          edited_body: edits[i] || null,
        }));

      const { data } = await campaignAPI.reviewContent(campaignData.run_id, {
        approved: false,
        piece_feedbacks: pieceFeedbacks,
      });
      setCampaignData(data);
      setFeedback({});
      setEdits({});
    } catch (err) {
      showToast('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleQuickAction = async (actionId) => {
    setQuickLoading(actionId);
    try {
      const { data } = await campaignAPI.quickAction(campaignData.run_id, {
        piece_index: activeTab,
        action: actionId,
      });
      // Update the piece body in local state
      const updatedPieces = [...pieces];
      updatedPieces[activeTab] = {
        ...updatedPieces[activeTab],
        body: data.new_body,
        word_count: data.word_count,
      };
      setCampaignData({
        ...campaignData,
        content: { ...campaignData.content, pieces: updatedPieces },
      });
      // Clear any manual edits for this tab
      const newEdits = { ...edits };
      delete newEdits[activeTab];
      setEdits(newEdits);
    } catch (err) {
      showToast('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setQuickLoading(null);
    }
  };

  const activePiece = pieces[activeTab];
  const needsChangeCount = Object.values(feedback).filter(f => f.needsChange).length;

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="mb-8">
        <h2 className="text-4xl font-bold mb-3 tracking-tight">Content Review</h2>
        <p className="text-lg opacity-70">
          Review từng piece content. Dùng Quick Actions hoặc chỉnh sửa trực tiếp.
        </p>
      </div>

      {/* Channel tabs */}
      <div className="flex gap-2 mb-6 whitespace-nowrap overflow-x-auto pb-2 scrollbar-hide">
        {pieces.map((piece, i) => (
          <button key={i} onClick={() => setActiveTab(i)}
                  className={`px-6 py-3 rounded-xl text-sm font-bold tracking-wide transition-all cursor-pointer border ${
                    activeTab === i 
                    ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white border-purple-500/50 shadow-[0_4px_15px_rgba(139,92,246,0.4)]' 
                    : 'bg-[#252540]/60 text-gray-400 border-white/5 hover:border-purple-500/50 hover:text-white'
                  }`}>
            {piece.channel.toUpperCase()} — {piece.deliverable.replace('_', ' ').toUpperCase()}
            {feedback[i]?.needsChange && <span className="ml-2 bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full text-xs">Cần sửa</span>}
          </button>
        ))}
      </div>

      {campaignData?.revision_count > 0 && (
          <p className="text-sm font-semibold text-yellow-400 mb-6 bg-yellow-400/10 inline-block px-4 py-2 rounded-lg border border-yellow-400/20">
             Đã chỉnh sửa (Revision): {campaignData.revision_count}/2
          </p>
      )}

      {/* Active piece content */}
      {activePiece && (
        <div key={activeTab} className="glass-panel p-8 rounded-2xl mb-4 animate-in fade-in duration-500">
          {/* Hook */}
          {activePiece.hook && (
            <div className="mb-6">
              <span className="inline-block text-xs font-bold px-3 py-1 rounded bg-yellow-400/20 text-yellow-400 border border-yellow-400/30 mb-3 tracking-wider">HOOK</span>
              <p className="text-xl font-medium leading-relaxed">{activePiece.hook}</p>
            </div>
          )}

          {/* Body — editable */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3 border-b border-white/10 pb-2">
              <span className="text-xs font-bold tracking-wider text-purple-400">BODY CONTENT</span>
              <button onClick={() => setEditMode({...editMode, [activeTab]: !editMode[activeTab]})}
                      className="text-xs px-4 py-1.5 rounded-lg cursor-pointer font-bold tracking-wide transition-all bg-white/5 hover:bg-white/10 border border-white/10">
                {editMode[activeTab] ? '👀 Preview' : '✏️ Chỉnh sửa tay'}
              </button>
            </div>

            {editMode[activeTab] ? (
              <textarea value={edits[activeTab] ?? activePiece.body}
                        onChange={e => setEdits({...edits, [activeTab]: e.target.value})}
                        rows={12}
                        className="w-full p-5 rounded-xl text-base font-medium glass-input resize-y placeholder:opacity-50"
                         />
            ) : (
              <div className="whitespace-pre-wrap text-base leading-relaxed p-6 rounded-xl bg-[#0f0f1a]/50 border border-white/5 shadow-inner text-gray-200">
                {edits[activeTab] ?? activePiece.body}
              </div>
            )}
          </div>

          {/* CTA */}
          {activePiece.cta_text && (
            <div className="p-4 rounded-xl mb-6 bg-emerald-500/10 border border-emerald-500/20 inline-block">
              <span className="text-xs font-bold tracking-wider text-emerald-400 mr-2">CTA: </span>
              <span className="text-base font-semibold">{activePiece.cta_text}</span>
            </div>
          )}

          {/* Hashtags */}
          {activePiece.hashtags?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {activePiece.hashtags.map((h, i) => (
                <span key={i} className="text-sm px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-300 font-medium">
                  {h}
                </span>
              ))}
            </div>
          )}
          {/* Visual Direction */}
          {activePiece.visual_direction && (
            <details className="mt-4 group mb-4">
              <summary className="text-xs font-bold tracking-wider text-purple-400 cursor-pointer list-none flex items-center gap-2">
                🎨 VISUAL DIRECTION (click để xem)
              </summary>
              <div className="mt-2 p-4 rounded-xl bg-[#0f0f1a]/50 border border-white/5 text-sm text-gray-300 whitespace-pre-wrap">
                {activePiece.visual_direction}
              </div>
            </details>
          )}

          {/* Notes */}
          {activePiece.notes && (
            <details className="mt-3 group mb-4">
              <summary className="text-xs font-bold tracking-wider text-blue-400 cursor-pointer list-none flex items-center gap-2">
                📝 NOTES (click để xem)
              </summary>
              <div className="mt-2 p-4 rounded-xl bg-[#0f0f1a]/50 border border-white/5 text-sm text-gray-300 whitespace-pre-wrap">
                {activePiece.notes}
              </div>
            </details>
          )}
          {/* Word count */}
          <div className="flex justify-between items-center mt-6 pt-4 border-t border-white/5">
            <p className="text-xs font-medium text-gray-500">
              {activePiece.word_count} words
            </p>
            <button onClick={() => {
              const text = formatForPlatform(activePiece);
              navigator.clipboard.writeText(text);
              showToast('Đã copy nội dung chuẩn cho đăng bài!', 'success');
            }}
            className="px-4 py-2 rounded-xl text-xs font-medium bg-white/5 border border-white/10 hover:bg-white/10 cursor-pointer text-gray-300">
              📋 Copy Content
            </button>
          </div>
        </div>
      )}

      {/* Quick Actions bar */}
      <div className="glass-panel p-4 rounded-2xl mb-6 flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold tracking-wider text-gray-400 mr-2">⚡ QUICK ACTIONS:</span>
        {QUICK_ACTIONS.map(action => (
          <button 
            key={action.id}
            onClick={() => handleQuickAction(action.id)}
            disabled={quickLoading !== null || loading}
            className={`px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-all cursor-pointer border border-white/10 hover:border-purple-500/40 hover:bg-purple-500/10 disabled:opacity-40 disabled:cursor-not-allowed ${
              quickLoading === action.id ? 'bg-purple-500/20 border-purple-500/40' : 'bg-white/5'
            }`}>
            {quickLoading === action.id ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <span>{action.label.split(' ')[0]}</span>
            )}
            {quickLoading === action.id ? 'Đang xử lý...' : action.label.split(' ').slice(1).join(' ')}
          </button>
        ))}
      </div>

      {/* Per-piece feedback */}
      <div className="glass-panel p-6 rounded-2xl mb-8">
        <label className="flex items-center gap-3 cursor-pointer group">
          <input type="checkbox"
                 checked={feedback[activeTab]?.needsChange || false}
                 onChange={e => setFeedback({
                   ...feedback,
                   [activeTab]: { ...feedback[activeTab], needsChange: e.target.checked }
                 })}
                 className="w-5 h-5 rounded text-red-500 focus:ring-red-500 bg-[#0f0f1a] border-gray-600 transition-all cursor-pointer" />
          <span className="text-base font-semibold group-hover:text-red-400 transition-colors">🔄 Piece này cần AI sinh lại (full pipeline)</span>
        </label>

        {feedback[activeTab]?.needsChange && (
          <textarea placeholder="Cần AI sửa gì? (ví dụ: hook yếu, dài quá...)"
                    value={feedback[activeTab]?.comment || ''}
                    onChange={e => setFeedback({
                      ...feedback,
                      [activeTab]: { ...feedback[activeTab], comment: e.target.value }
                    })}
                    rows={2}
                    className="w-full mt-4 p-4 rounded-xl text-base glass-input resize-y animate-in fade-in slide-in-from-top-2" />
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-4">
        <button onClick={() => setPhase('strategy_review')} disabled={loading}
                className="px-6 py-4 rounded-xl text-base font-semibold flex items-center justify-center gap-2 cursor-pointer btn-secondary">
          <ArrowLeft className="w-5 h-5" />
          Strategy
        </button>
        {needsChangeCount > 0 ? (
          <button onClick={handleRevise} disabled={loading}
                  className="w-full py-4 rounded-xl text-base font-semibold flex items-center justify-center gap-2 cursor-pointer btn-secondary">
             {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <RotateCcw className="w-5 h-5" />}
            🔄 Gửi AI gen lại ({needsChangeCount} pieces)
          </button>
        ) : (
          <button onClick={handleApprove} disabled={loading}
                  className="w-full py-4 rounded-xl text-base font-semibold flex items-center justify-center gap-2 cursor-pointer bg-emerald-500 hover:bg-emerald-400 text-white shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all">
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />}
            ✅ Nội dung OK, Go to Review
          </button>
        )}
      </div>
      <LoadingOverlay
        show={loading}
        title="Đang xử lý content..."
        description="AI đang review hoặc tái tạo lại nội dung cho bạn."
      />
      <Toast />
    </div>
  );
}
