import { useState } from 'react';
import { campaignAPI } from '../api/client';
import { Loader2, ArrowLeft } from 'lucide-react';
import { useToast } from '../components/Toast';
import LoadingOverlay from '../components/LoadingOverlay';
import { useProgress } from '../hooks/useProgress';

const GOAL_LABEL = {
  awareness: 'Nhận diện',
  engagement: 'Tương tác',
  lead_generation: 'Thu khách tiềm năng',
  conversion: 'Chuyển đổi mua hàng',
  retention: 'Giữ chân khách',
};

const CHANNELS = [
  { v: 'facebook', l: 'Facebook' },
  { v: 'instagram', l: 'Instagram' },
  { v: 'tiktok', l: 'TikTok' },
];

export default function BriefReviewPage({ campaignData, setCampaignData, setPhase, loading, setLoading }) {
  const { showToast, Toast } = useToast();
  const { steps, start, stop } = useProgress();
  const brief = campaignData?.brief;
  const contextInfo = campaignData?.context_info;
  const [editMode, setEditMode] = useState(false);
  const [editedBrief, setEditedBrief] = useState(brief ? {
    goal: brief.goal,
    product: brief.offer.product_or_service,
    audience: brief.audience.persona_description,
    channels: brief.channels,
    key_message: brief.offer.key_message,
    cta: brief.offer.cta,
  } : {});

  if (!brief) return null;

  const handleApprove = async () => {
    setLoading(true);
    await start(campaignData.run_id); // mở luồng tiến trình trước khi POST
    try {
      const { data } = await campaignAPI.approveBrief(campaignData.run_id, editMode ? editedBrief : null);
      setCampaignData(data);
      setPhase('strategy_review');
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
        <h1 className="t-page mb-2.5">Duyệt brief</h1>
        <p className="t-lede">
          Đây là cách hệ thống hiểu đề bài của bạn. Sai chỗ nào thì sửa ngay — mọi bước sau đều dựa vào đây.
        </p>
      </header>

      {!editMode ? (
        <dl className="sheet spot mb-6">
          <Row label="Mục tiêu" value={GOAL_LABEL[brief.goal] || brief.goal} />
          <Row label="Sản phẩm / dịch vụ" value={brief.offer.product_or_service} />
          <Row label="Đối tượng" value={brief.audience.persona_description} />
          <Row
            label="Kênh đăng"
            value={brief.channels.map(c => CHANNELS.find(x => x.v === c)?.l || c).join(' · ')}
          />
          <Row label="Thông điệp cốt lõi" value={brief.offer.key_message} />
          <Row label="Kêu gọi hành động" value={brief.offer.cta} last />
        </dl>
      ) : (
        <div className="sheet p-6 mb-6 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5">
          <div>
            <label htmlFor="e-goal" className="t-label block mb-2">Mục tiêu</label>
            <select
              id="e-goal"
              value={editedBrief.goal}
              onChange={e => setEditedBrief({ ...editedBrief, goal: e.target.value })}
              className="field"
            >
              {Object.entries(GOAL_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>

          <div>
            <p className="t-label mb-2">Kênh đăng</p>
            <div className="flex flex-wrap gap-2">
              {CHANNELS.map(ch => (
                <button
                  key={ch.v}
                  onClick={() => {
                    const channels = editedBrief.channels.includes(ch.v)
                      ? editedBrief.channels.filter(c => c !== ch.v)
                      : [...editedBrief.channels, ch.v];
                    setEditedBrief({ ...editedBrief, channels });
                  }}
                  data-on={editedBrief.channels.includes(ch.v)}
                  className="chip"
                >
                  {ch.l}
                </button>
              ))}
            </div>
          </div>

          <EditField id="e-product" label="Sản phẩm / dịch vụ" value={editedBrief.product}
                     onChange={v => setEditedBrief({ ...editedBrief, product: v })} />
          <EditField id="e-msg" label="Thông điệp cốt lõi" value={editedBrief.key_message}
                     onChange={v => setEditedBrief({ ...editedBrief, key_message: v })} />
          <EditField id="e-aud" label="Đối tượng" value={editedBrief.audience}
                     onChange={v => setEditedBrief({ ...editedBrief, audience: v })} />
          <EditField id="e-cta" label="Kêu gọi hành động" value={editedBrief.cta}
                     onChange={v => setEditedBrief({ ...editedBrief, cta: v })} />
        </div>
      )}

      {/* Nguồn kiến thức đã nạp — minh bạch để người dùng biết AI đang dựa vào gì */}
      {contextInfo && (
        <section className="mb-8">
          <p className="t-label mb-2.5">Kiến thức đã nạp</p>
          <div className="sheet px-5 py-4">
            <div className="flex flex-wrap gap-x-8 gap-y-2 mb-3">
              <Meta label="Chế độ" value={contextInfo.mode === 'branded' ? 'Theo brand' : 'Không brand'} />
              {contextInfo.brand_name && <Meta label="Brand" value={contextInfo.brand_name} />}
              <Meta label="Số tài liệu" value={contextInfo.loaded_docs?.length || 0} />
            </div>
            {contextInfo.loaded_docs?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-3 border-t border-rule">
                {contextInfo.loaded_docs.map((doc, i) => (
                  <span key={i} className="font-data text-[0.75rem] text-ink-2 bg-inset px-1.5 py-0.5 rounded-[2px]">
                    {doc}
                  </span>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      <div className="flex flex-wrap gap-2.5 pt-6 border-t border-rule">
        <button onClick={() => setPhase('input')} disabled={loading} className="btn btn-quiet">
          <ArrowLeft className="w-4 h-4" /> Đề bài
        </button>
        <button onClick={() => setEditMode(!editMode)} disabled={loading} className="btn btn-default">
          {editMode ? 'Xong' : 'Sửa brief'}
        </button>
        <button onClick={handleApprove} disabled={loading} className="btn btn-primary">
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          {loading ? 'Đang dựng chiến lược' : 'Duyệt, dựng chiến lược'}
        </button>
      </div>

      <LoadingOverlay
        show={loading}
        steps={steps}
        title="Đang dựng chiến lược"
        description="Đào insight từ đối tượng trước, rồi mới lên hướng tiếp cận."
      />
      <Toast />
    </div>
  );
}

function Row({ label, value, last }) {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-[168px_1fr] gap-1 sm:gap-5 px-5 py-3.5 ${last ? '' : 'border-b border-rule'}`}>
      <dt className="t-label sm:pt-[3px]">{label}</dt>
      <dd className="text-[0.9375rem] leading-relaxed text-ink">{value || <span className="text-ink-3">—</span>}</dd>
    </div>
  );
}

function Meta({ label, value }) {
  return (
    <div>
      <p className="t-label">{label}</p>
      <p className="text-[0.875rem] mt-0.5">{value}</p>
    </div>
  );
}

function EditField({ id, label, value, onChange }) {
  return (
    <div>
      <label htmlFor={id} className="t-label block mb-2">{label}</label>
      <input id={id} value={value} onChange={e => onChange(e.target.value)} className="field" />
    </div>
  );
}
