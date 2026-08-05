import { useState } from 'react';
import { campaignAPI } from '../api/client';
import { Loader2, ArrowLeft } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useToast } from '../components/Toast';
import LoadingOverlay from '../components/LoadingOverlay';
import { useProgress } from '../hooks/useProgress';

const FEEDBACK_OPTIONS = [
  { key: 'tone',     label: 'Tone chưa phù hợp' },
  { key: 'angle',    label: 'Góc tiếp cận chưa đúng' },
  { key: 'audience', label: 'Chưa hiểu đúng đối tượng' },
  { key: 'hook',     label: 'Hook chưa đủ mạnh' },
  { key: 'cta',      label: 'Kêu gọi hành động chưa rõ' },
  { key: 'platform', label: 'Cách dùng kênh chưa đúng' },
];

export default function StrategyReviewPage({ campaignData, setCampaignData, setPhase, loading, setLoading }) {
  const { showToast, Toast } = useToast();
  const { steps, start, stop } = useProgress();
  const [checks, setChecks] = useState([]);
  const [comment, setComment] = useState('');

  const hasFeedback = checks.length > 0 || comment.trim().length > 0;

  const handleApprove = async () => {
    setLoading(true);
    await start(campaignData.run_id);
    try {
      const { data } = await campaignAPI.reviewStrategy(campaignData.run_id, {
        approved: true, feedback_checks: [], comment: null,
      });
      setCampaignData(data);
      setPhase('content_review');
    } catch (err) {
      showToast(err.response?.data?.detail?.message || err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
      stop();
    }
  };

  const handleRevise = async () => {
    if (!hasFeedback) {
      showToast('Chọn ít nhất một vấn đề hoặc viết ghi chú.');
      return;
    }
    setLoading(true);
    await start(campaignData.run_id);
    try {
      const { data } = await campaignAPI.reviewStrategy(campaignData.run_id, {
        approved: false, feedback_checks: checks, comment,
      });
      setCampaignData(data);
      setComment('');
      setChecks([]);
    } catch (err) {
      showToast(err.response?.data?.detail?.message || err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
      stop();
    }
  };

  return (
    <div className="rise">
      <header className="mb-8">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="t-page mb-2.5">Duyệt chiến lược</h1>
            <p className="t-lede">
              Hướng tiếp cận trước khi viết chữ nào. Nếu góc nhìn ở đây sai thì nội dung sau cũng sai.
            </p>
          </div>
          {campaignData?.revision_count > 0 && (
            <span className="tag tag-warn shrink-0 num">
              Sửa lần {campaignData.revision_count}
            </span>
          )}
        </div>
      </header>

      {/* Bản chiến lược — đọc như tài liệu, không như thẻ giao diện */}
      <article className="sheet spot px-6 py-7 md:px-10 md:py-10 mb-9">
        <div className="md">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {campaignData?.strategy || ''}
          </ReactMarkdown>
        </div>
      </article>

      <section className="mb-8">
        <h2 className="t-section mb-1.5">Cần chỉnh gì không?</h2>
        <p className="text-[0.875rem] text-ink-2 mb-4 max-w-[58ch]">
          Bỏ qua phần này nếu chiến lược đã ổn. Chọn vấn đề để hệ thống viết lại đúng chỗ.
        </p>

        <div className="flex flex-wrap gap-2 mb-4">
          {FEEDBACK_OPTIONS.map(opt => {
            const on = checks.includes(opt.key);
            return (
              <button
                key={opt.key}
                onClick={() => setChecks(on ? checks.filter(c => c !== opt.key) : [...checks, opt.key])}
                data-on={on}
                aria-pressed={on}
                className="chip"
              >
                {opt.label}
              </button>
            );
          })}
        </div>

        <label htmlFor="strategy-note" className="t-label block mb-2">Ghi chú thêm</label>
        <textarea
          id="strategy-note"
          value={comment}
          onChange={e => setComment(e.target.value)}
          rows={4}
          className="field"
          placeholder="Ví dụ: đổi lời kêu gọi thành nhắn tin cho fanpage; bớt phần nói về giá."
        />
      </section>

      <div className="flex flex-wrap gap-2.5 pt-6 border-t border-rule">
        <button onClick={() => setPhase('brief_review')} disabled={loading} className="btn btn-quiet">
          <ArrowLeft className="w-4 h-4" /> Brief
        </button>
        <button onClick={handleRevise} disabled={loading || !hasFeedback} className="btn btn-default">
          Viết lại chiến lược
        </button>
        <button onClick={handleApprove} disabled={loading} className="btn btn-primary">
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          {loading ? 'Đang viết nội dung' : 'Duyệt, viết nội dung'}
        </button>
      </div>

      <LoadingOverlay
        show={loading}
        steps={steps}
        title={hasFeedback ? 'Đang viết lại chiến lược' : 'Đang viết nội dung'}
        description={hasFeedback
          ? 'Hệ thống đang dựng lại hướng tiếp cận theo ghi chú của bạn.'
          : 'Mỗi kênh được viết riêng theo đặc thù của nền tảng đó.'}
      />
      <Toast />
    </div>
  );
}
