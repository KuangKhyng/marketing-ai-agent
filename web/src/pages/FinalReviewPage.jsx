import { motion } from 'framer-motion';
import { campaignAPI } from '../api/client';
import { Loader2, ArrowLeft } from 'lucide-react';
import { useToast } from '../components/Toast';
import LoadingOverlay from '../components/LoadingOverlay';

/* Ngưỡng đạt khớp với THRESHOLDS trong src/nodes/reviewer.py.
   Hiển thị ngưỡng để người dùng biết còn cách bao xa, thay vì chỉ thấy đạt/trượt. */
const DIMENSIONS = {
  brand_fit:     { label: 'Hợp brand',        threshold: 0.7 },
  factuality:    { label: 'Đúng sự thật',     threshold: 0.9 },
  channel_fit:   { label: 'Hợp kênh',         threshold: 0.6 },
  business_fit:  { label: 'Hợp mục tiêu KD',  threshold: 0.7 },
  content_depth: { label: 'Chiều sâu',        threshold: 0.7 },
};

export default function FinalReviewPage({ campaignData, setCampaignData, setPhase, loading, setLoading }) {
  const { showToast, Toast } = useToast();
  const result = campaignData?.review_result;

  const handleApprove = async () => {
    setLoading(true);
    try {
      const { data } = await campaignAPI.approveFinal(campaignData.run_id);
      setCampaignData(data);
      setPhase('export');
    } catch (err) {
      showToast(err.response?.data?.detail?.message || err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!result) return null;

  const failed = result.dimension_scores.filter(s => !s.passed).length;
  const unavailable = result.review_unavailable;

  const verdict = unavailable
    ? 'Chưa chấm được — reviewer gặp lỗi'
    : result.overall_passed
      ? 'Đạt cả năm chiều, sẵn sàng bàn giao'
      : `Chưa đạt ${failed}/${result.dimension_scores.length} chiều`;

  return (
    <div className="rise">
      <header className="mb-8">
        <h1 className="t-page mb-2.5">Chấm chất lượng</h1>
        <p className="t-lede">
          Nội dung được đối chiếu trên năm chiều. Đây là ý kiến tham khảo — bạn vẫn giữ quyền quyết định.
        </p>
      </header>

      {/* Kết luận đặt trước chi tiết */}
      <div className="sheet spot px-5 py-4 mb-8 flex items-center justify-between gap-4 flex-wrap"
           style={{ borderLeft: `2px solid ${result.overall_passed ? 'var(--pass)' : 'var(--fail)'}` }}>
        <div>
          <p className="t-label mb-1">Kết luận</p>
          <p className="font-copy text-[1.125rem] font-semibold">{verdict}</p>
          {unavailable && (
            <p className="mt-1.5 text-[0.875rem] text-ink-2 leading-relaxed">
              Hệ thống không chấm được lần này, nên chưa có gì bảo đảm về chất lượng.
              Cần đọc lại toàn bộ trước khi dùng, hoặc quay lại chấm lần nữa.
            </p>
          )}
        </div>
        <span className={`tag ${result.overall_passed ? 'tag-pass' : 'tag-fail'}`}>
          {unavailable ? 'Chưa kiểm' : result.overall_passed ? 'Đạt' : 'Cần xem lại'}
        </span>
      </div>

      {/* Lề chấm bài — mỗi chiều một dòng, có vạch ngưỡng */}
      <section className="mb-8">
        <p className="t-label mb-3">Chi tiết từng chiều</p>
        <div className="sheet">
          {result.dimension_scores.map((s, i, arr) => {
            const meta = DIMENSIONS[s.dimension] || { label: s.dimension.replace(/_/g, ' '), threshold: 0.7 };
            const pct = Math.max(0, Math.min(1, s.score)) * 100;
            return (
              <motion.div
                key={s.dimension}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * .07, duration: .4, ease: [.16, 1, .3, 1] }}
                className={`px-5 py-4 ${i < arr.length - 1 ? 'border-b border-rule' : ''}`}
              >
                <div className="flex items-baseline justify-between gap-4 mb-2">
                  <span className="text-[0.9375rem] font-medium">{meta.label}</span>
                  <span className="font-data text-[0.8125rem] num shrink-0"
                        style={{ color: s.passed ? 'var(--pass)' : 'var(--fail)' }}>
                    {s.score.toFixed(2)}
                    <span className="text-ink-3"> / cần {meta.threshold.toFixed(2)}</span>
                  </span>
                </div>

                {/* Thanh đo có vạch ngưỡng — thấy ngay còn thiếu bao nhiêu */}
                <div className="relative h-[6px] mb-2.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,.06)' }}>
                  <motion.div
                    className="absolute inset-y-0 left-0 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: .8, delay: i * .09, ease: [.16, 1, .3, 1] }}
                    style={{ background: s.passed ? 'var(--pass)' : 'var(--fail)' }}
                  />
                  <div
                    className="absolute inset-y-[-3px] w-px"
                    style={{ left: `${meta.threshold * 100}%`, background: 'var(--ink)' }}
                    title={`Ngưỡng đạt ${meta.threshold}`}
                  />
                </div>

                <p className="text-[0.875rem] text-ink-2 leading-relaxed">{s.feedback}</p>

                {/* Vi phạm quy tắc cứng — kiểm bằng code, làm chiều này trượt
                    bất kể điểm. Trước đây tính xong rồi không hiện ở đâu. */}
                {s.rule_violations?.length > 0 && (
                  <ul className="mt-2.5 space-y-1 pl-3 border-l border-rule">
                    {s.rule_violations.map((v, k) => (
                      <li key={k} className="font-data text-[0.8125rem] text-ink-2 leading-relaxed">
                        {v}
                      </li>
                    ))}
                  </ul>
                )}
              </motion.div>
            );
          })}
        </div>
        <p className="mt-2 text-[0.8125rem] text-ink-3">
          Vạch dọc là ngưỡng đạt của từng chiều. Vi phạm quy tắc cứng làm chiều đó trượt kể cả khi điểm vượt ngưỡng.
        </p>
      </section>

      {result.critical_issues?.length > 0 && (
        <section className="mb-8">
          <p className="t-label mb-2.5">Vấn đề phát hiện được ({result.critical_issues.length})</p>
          <div className="sheet px-5 py-4" style={{ borderLeft: '2px solid var(--fail)' }}>
            <ul className="space-y-1.5">
              {result.critical_issues.map((issue, i) => (
                <li key={i} className="text-[0.875rem] text-ink-2 leading-relaxed">{issue}</li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {result.revision_instructions && (
        <section className="mb-8">
          <p className="t-label mb-2.5">Gợi ý sửa</p>
          <div className="sheet px-5 py-4" style={{ borderLeft: '2px solid var(--warn)' }}>
            <p className="text-[0.9375rem] leading-relaxed whitespace-pre-wrap text-ink-2">
              {result.revision_instructions}
            </p>
          </div>
        </section>
      )}

      <div className="flex flex-wrap gap-2.5 pt-6 border-t border-rule">
        <button onClick={() => setPhase('content_review')} disabled={loading} className="btn btn-quiet">
          <ArrowLeft className="w-4 h-4" /> Sửa nội dung
        </button>
        <button onClick={handleApprove} disabled={loading} className="btn btn-primary">
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          {result.overall_passed ? 'Bàn giao' : 'Vẫn bàn giao'}
        </button>
      </div>

      <LoadingOverlay show={loading} title="Đang kết xuất" description="Ghi file bàn giao." hint="Thường mất vài giây." />
      <Toast />
    </div>
  );
}
