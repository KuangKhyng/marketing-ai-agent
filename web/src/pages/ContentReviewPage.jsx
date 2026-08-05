import { useState } from 'react';
import { motion } from 'framer-motion';
import { campaignAPI } from '../api/client';
import { Loader2, ArrowLeft, Check } from 'lucide-react';
import { useToast } from '../components/Toast';
import LoadingOverlay from '../components/LoadingOverlay';
import { useProgress } from '../hooks/useProgress';

const CHANNEL_LABEL = { facebook: 'Facebook', instagram: 'Instagram', tiktok: 'TikTok' };
const DELIVERABLE_LABEL = {
  post: 'Bài đăng',
  carousel: 'Carousel',
  reels_script: 'Kịch bản Reels',
  short_video_script: 'Kịch bản video ngắn',
  story: 'Story',
};

const QUICK_ACTIONS = [
  { id: 'rewrite',     label: 'Viết lại' },
  { id: 'change_hook', label: 'Đổi hook' },
  { id: 'shorter',     label: 'Ngắn hơn' },
  { id: 'change_tone', label: 'Đổi tone' },
];

function formatForPlatform(piece) {
  let text = '';
  if (piece.body) text += piece.body;
  if (piece.cta_text) text += '\n\n' + piece.cta_text;
  if (piece.hashtags?.length) text += '\n\n' + piece.hashtags.join(' ');
  return text;
}

export default function ContentReviewPage({ campaignData, setCampaignData, setPhase, loading, setLoading }) {
  const { showToast, Toast } = useToast();
  const { steps, start, stop } = useProgress();
  const pieces = campaignData?.content?.pieces || [];
  const [activeTab, setActiveTab] = useState(0);
  const [editMode, setEditMode] = useState({});
  const [edits, setEdits] = useState({});
  const [feedback, setFeedback] = useState({});
  const [quickLoading, setQuickLoading] = useState(null);

  const activePiece = pieces[activeTab];
  const needsChangeCount = Object.values(feedback).filter(f => f.needsChange).length;

  const handleApprove = async () => {
    setLoading(true);
    await start(campaignData.run_id);
    try {
      const pieceFeedbacks = pieces.map((_, i) => ({
        piece_index: i,
        approved: !feedback[i]?.needsChange,
        comment: feedback[i]?.comment || null,
        edited_body: edits[i] || null,
      }));
      const { data } = await campaignAPI.reviewContent(campaignData.run_id, {
        approved: true, piece_feedbacks: pieceFeedbacks,
      });
      setCampaignData(data);
      setPhase('final_review');
    } catch (err) {
      showToast(err.response?.data?.detail?.message || err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
      stop();
    }
  };

  const handleRevise = async () => {
    setLoading(true);
    await start(campaignData.run_id);
    try {
      const pieceFeedbacks = Object.entries(feedback)
        .filter(([, fb]) => fb.needsChange)
        .map(([i, fb]) => ({
          piece_index: parseInt(i, 10),
          approved: false,
          comment: fb.comment,
          edited_body: edits[i] || null,
        }));
      const { data } = await campaignAPI.reviewContent(campaignData.run_id, {
        approved: false, piece_feedbacks: pieceFeedbacks,
      });
      setCampaignData(data);
      setFeedback({});
      setEdits({});
    } catch (err) {
      showToast(err.response?.data?.detail?.message || err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
      stop();
    }
  };

  const handleQuickAction = async (actionId) => {
    setQuickLoading(actionId);
    try {
      const { data } = await campaignAPI.quickAction(campaignData.run_id, {
        piece_index: activeTab, action: actionId,
      });
      const updatedPieces = [...pieces];
      updatedPieces[activeTab] = { ...updatedPieces[activeTab], body: data.new_body, word_count: data.word_count };
      setCampaignData({ ...campaignData, content: { ...campaignData.content, pieces: updatedPieces } });
      const newEdits = { ...edits };
      delete newEdits[activeTab];
      setEdits(newEdits);
    } catch (err) {
      showToast(err.response?.data?.detail?.message || err.response?.data?.detail || err.message);
    } finally {
      setQuickLoading(null);
    }
  };

  return (
    <div className="rise">
      <header className="mb-7">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="t-page mb-2.5">Duyệt nội dung</h1>
            <p className="t-lede">
              Đọc từng bài như bản thảo. Sửa tay được ngay, hoặc để hệ thống viết lại.
            </p>
          </div>
          {campaignData?.revision_count > 0 && (
            <span className="tag tag-warn shrink-0 num">Sửa lần {campaignData.revision_count}/2</span>
          )}
        </div>
      </header>

      {/* Chọn bài — gạch chân trượt giữa các tab bằng shared layout */}
      <div className="scroll-x border-b border-rule mb-7">
        <div className="flex gap-6 min-w-max">
          {pieces.map((piece, i) => {
            const on = activeTab === i;
            const flagged = feedback[i]?.needsChange;
            return (
              <button
                key={i}
                onClick={() => setActiveTab(i)}
                aria-current={on ? 'true' : undefined}
                className="relative pb-3 text-left"
              >
                <span
                  className="block text-[0.875rem] transition-colors"
                  style={{ color: on ? 'var(--ink)' : 'var(--ink-2)', fontWeight: on ? 500 : 400 }}
                >
                  {CHANNEL_LABEL[piece.channel] || piece.channel}
                </span>
                <span className="block mt-0.5 text-[0.75rem] text-ink-3">
                  {DELIVERABLE_LABEL[piece.deliverable] || piece.deliverable}
                  {flagged && <span style={{ color: 'var(--fail)' }}> · cần sửa</span>}
                </span>
                {on && (
                  <motion.span
                    layoutId="piece-tab"
                    className="absolute left-0 right-0 -bottom-px h-[2px] rounded-full"
                    style={{ background: 'var(--cham)', boxShadow: '0 0 10px var(--cham-glow)' }}
                    transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                  />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {activePiece && (
        <>
          {/* Tờ bản thảo */}
          <article key={activeTab} className="sheet spot px-6 py-7 md:px-10 md:py-9 mb-4 rise">
            {activePiece.hook && (
              <div className="mb-6">
                <p className="t-label mb-2">Hook</p>
                <p className="font-copy text-[1.25rem] leading-snug font-semibold">{activePiece.hook}</p>
              </div>
            )}

            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <p className="t-label">Nội dung</p>
                <button
                  onClick={() => setEditMode({ ...editMode, [activeTab]: !editMode[activeTab] })}
                  className="btn btn-quiet !py-1.5 !px-2.5 !text-[13px]"
                >
                  {editMode[activeTab] ? 'Xem bản đọc' : 'Sửa tay'}
                </button>
              </div>

              {editMode[activeTab] ? (
                <textarea
                  value={edits[activeTab] ?? activePiece.body}
                  onChange={e => setEdits({ ...edits, [activeTab]: e.target.value })}
                  rows={14}
                  className="field font-copy !text-[1.0625rem]"
                />
              ) : (
                <div className="t-copy whitespace-pre-wrap">
                  {edits[activeTab] ?? activePiece.body}
                </div>
              )}
            </div>

            {activePiece.cta_text && (
              <div className="mb-5">
                <p className="t-label mb-1.5">Kêu gọi hành động</p>
                <p className="font-copy text-[1.0625rem]">{activePiece.cta_text}</p>
              </div>
            )}

            {activePiece.hashtags?.length > 0 && (
              <div className="mb-5">
                <p className="t-label mb-1.5">Hashtag</p>
                <p className="font-data text-[0.8125rem] text-ink-2 leading-relaxed break-words">
                  {activePiece.hashtags.join('  ')}
                </p>
              </div>
            )}

            {(activePiece.visual_direction || activePiece.notes) && (
              <div className="border-t border-rule pt-4 mb-4 space-y-3">
                {activePiece.visual_direction && (
                  <Detail label="Gợi ý hình ảnh" text={activePiece.visual_direction} />
                )}
                {activePiece.notes && <Detail label="Ghi chú" text={activePiece.notes} />}
              </div>
            )}

            <div className="flex items-center justify-between gap-3 pt-4 border-t border-rule">
              <span className="t-data num">{activePiece.word_count} từ</span>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(formatForPlatform(activePiece));
                  showToast('Đã sao chép, dán thẳng lên được.', 'success');
                }}
                className="btn btn-default !py-2 !px-3 !text-[13px]"
              >
                Sao chép
              </button>
            </div>
          </article>

          {/* Sửa nhanh — một lượt gọi rẻ, không chạy lại cả dây chuyền */}
          <div className="flex flex-wrap items-center gap-2 mb-8">
            <span className="t-label mr-1">Sửa nhanh</span>
            {QUICK_ACTIONS.map(action => (
              <button
                key={action.id}
                onClick={() => handleQuickAction(action.id)}
                disabled={quickLoading !== null || loading}
                className="btn btn-default !py-2 !px-3 !text-[13px]"
              >
                {quickLoading === action.id && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                {action.label}
              </button>
            ))}
          </div>

          {/* Đánh dấu viết lại toàn bộ */}
          <div className="sheet px-5 py-4 mb-8">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={feedback[activeTab]?.needsChange || false}
                onChange={e => setFeedback({
                  ...feedback,
                  [activeTab]: { ...feedback[activeTab], needsChange: e.target.checked },
                })}
                className="mt-0.5 w-4 h-4 shrink-0 accent-[var(--cham)]"
              />
              <span>
                <span className="block text-[0.9375rem]">Viết lại bài này từ đầu</span>
                <span className="block text-[0.8125rem] text-ink-2 mt-0.5">
                  Chạy lại cả dây chuyền cho bài này — chậm hơn sửa nhanh, nhưng đổi được cả hướng.
                </span>
              </span>
            </label>

            {feedback[activeTab]?.needsChange && (
              <textarea
                value={feedback[activeTab]?.comment || ''}
                onChange={e => setFeedback({
                  ...feedback,
                  [activeTab]: { ...feedback[activeTab], comment: e.target.value },
                })}
                rows={2}
                className="field mt-3 rise"
                placeholder="Cần sửa gì? Ví dụ: mở bài yếu, dài quá, chưa đúng giọng brand."
              />
            )}
          </div>
        </>
      )}

      <div className="flex flex-wrap gap-2.5 pt-6 border-t border-rule">
        <button onClick={() => setPhase('strategy_review')} disabled={loading} className="btn btn-quiet">
          <ArrowLeft className="w-4 h-4" /> Chiến lược
        </button>
        {needsChangeCount > 0 ? (
          <button onClick={handleRevise} disabled={loading} className="btn btn-primary">
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            Viết lại {needsChangeCount} bài
          </button>
        ) : (
          <button onClick={handleApprove} disabled={loading} className="btn btn-go">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
            Duyệt, chấm chất lượng
          </button>
        )}
      </div>

      <LoadingOverlay
        show={loading}
        steps={steps}
        title={needsChangeCount > 0 ? 'Đang viết lại' : 'Đang chấm chất lượng'}
        description={needsChangeCount > 0
          ? 'Hệ thống dựng lại nội dung theo ghi chú của bạn.'
          : 'Đối chiếu nội dung với brand, sự thật, đặc thù kênh và chiều sâu.'}
      />
      <Toast />
    </div>
  );
}

function Detail({ label, text }) {
  return (
    <details className="group">
      <summary className="t-label cursor-pointer list-none hover:text-ink-2 select-none">
        {label}
        <span className="ml-1.5 font-normal tracking-normal normal-case text-ink-3 group-open:hidden">
          — mở
        </span>
      </summary>
      <p className="mt-2 text-[0.875rem] text-ink-2 leading-relaxed whitespace-pre-wrap">{text}</p>
    </details>
  );
}
