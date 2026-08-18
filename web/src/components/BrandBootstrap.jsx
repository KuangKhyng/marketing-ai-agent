import { useState } from 'react';
import { brandsAPI } from '../api/client';
import { Loader2, Plus, X, Check } from 'lucide-react';
import DraftReview from './DraftReview';
import { countChosen } from '../utils/draft';
import { formatCost } from '../utils/cost';

/*
 * Nạp liệu cho knowledge base của brand.
 *
 * Hai chặng, tích luỹ dần:
 *   1. Dán bài đã đăng   -> rút giọng văn + khung bài
 *   2. Dán tài liệu brand -> rút bộ khung brand
 *
 * Cả hai chặng chỉ ĐỀ XUẤT. Người dùng đối chiếu với nội dung đang có rồi mới
 * chọn lưu — knowledge_base là nguồn sự thật mà reviewer dùng để chấm tính
 * đúng đắn của content, nên không được để LLM ghi thẳng vào.
 */

const STAGES = {
  voice: {
    label: 'Bài đã đăng',
    lede: 'Dán vài bài bạn từng đăng. Hệ thống đọc để rút ra giọng văn và khung bài quen thuộc của brand.',
    itemLabel: 'Bài',
    placeholder:
      'Dán nguyên văn một bài đã đăng, kể cả emoji và hashtag.\n\nCàng nhiều bài thì càng rút được đúng, 3–5 bài là đủ dùng.',
    call: (brandId, chunks) => brandsAPI.bootstrapVoice(brandId, chunks),
    estimatePayload: (chunks) => ({ samples: chunks, documents: [] }),
  },
  brand: {
    label: 'Tài liệu brand',
    lede: 'Dán hồ sơ công ty, mô tả sản phẩm, ghi chú về khách hàng. Hệ thống sắp xếp thành bộ khung brand.',
    itemLabel: 'Tài liệu',
    placeholder:
      'Dán tài liệu về brand: bạn bán gì, cho ai, điều gì khiến khách chọn bạn.\n\nCó gì dán nấy — thiếu chỗ nào hệ thống sẽ nói ra chỗ đó.',
    call: (brandId, chunks) => brandsAPI.bootstrapBrand(brandId, chunks),
    estimatePayload: (chunks) => ({ samples: [], documents: chunks }),
  },
};

export default function BrandBootstrap({ brandId, onApplied, showToast }) {
  const [stage, setStage] = useState('voice');
  const [chunks, setChunks] = useState(['']);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState(null);
  // Hỏi giá trước khi đọc — xem BrandCreate, cùng lý do
  const [estimate, setEstimate] = useState(null);
  const [chosen, setChosen] = useState({});      // path -> bool
  const [takeVoice, setTakeVoice] = useState(true);
  const [takeMeta, setTakeMeta] = useState(true);

  const cfg = STAGES[stage];
  const filled = chunks.filter(c => c.trim().length > 0);

  const switchStage = (next) => {
    setStage(next);
    setChunks(['']);
    setDraft(null);
    setEstimate(null);
  };

  const handleAskPrice = async () => {
    setBusy(true);
    try {
      const { data } = await brandsAPI.bootstrapEstimate(cfg.estimatePayload(filled));
      if (data.cached) {
        await handleExtract();
      } else {
        setEstimate(data);
      }
    } catch {
      setEstimate({ estimated_cost: null, input_chars: 0, cached: false });
    } finally {
      setBusy(false);
    }
  };

  const handleExtract = async () => {
    setBusy(true);
    setDraft(null);
    setEstimate(null);
    try {
      const { data } = await cfg.call(brandId, filled);
      setDraft(data);
      // Mặc định chọn hết — người dùng bỏ chọn thứ không muốn, nhanh hơn
      setChosen(Object.fromEntries(data.files.map(f => [f.path, true])));
      setTakeVoice(Boolean(data.voice_profile));
      setTakeMeta(Object.keys(data.brand_meta || {}).length > 0);
    } catch (err) {
      showToast(
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        'Không đọc được tài liệu. Thử lại sau.'
      );
    } finally {
      setBusy(false);
    }
  };

  const handleApply = async () => {
    setBusy(true);
    try {
      await brandsAPI.bootstrapApply(brandId, {
        files: draft.files.filter(f => chosen[f.path]),
        voice_profile: takeVoice ? draft.voice_profile : null,
        brand_meta: takeMeta ? draft.brand_meta : null,
      });
      showToast('Đã lưu vào kho brand.');
      setDraft(null);
      setChunks(['']);
      if (onApplied) onApplied();
    } catch (err) {
      showToast(err.response?.data?.detail?.message || 'Không lưu được.');
    } finally {
      setBusy(false);
    }
  };

  const soChon = countChosen(draft, chosen, takeVoice, takeMeta);

  return (
    <div>
      {/* Chọn chặng */}
      <div className="inline-flex border border-rule-strong rounded-[3px] overflow-hidden mb-5">
        {Object.entries(STAGES).map(([id, s], i) => (
          <button
            key={id}
            onClick={() => switchStage(id)}
            disabled={busy}
            className={`px-4 py-2.5 text-[0.875rem] transition-colors ${i > 0 ? 'border-l border-rule-strong' : ''} ${
              stage === id ? 'bg-cham text-on-cham font-semibold' : 'bg-sheet text-ink-2 hover:bg-inset'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <p className="t-lede mb-6">{cfg.lede}</p>

      {/* Nhập liệu */}
      {!draft && (
        <>
          <div className="space-y-4 mb-4">
            {chunks.map((chunk, i) => (
              <div key={i}>
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor={`chunk-${i}`} className="t-label">
                    {cfg.itemLabel} {i + 1}
                  </label>
                  {chunks.length > 1 && (
                    <button
                      onClick={() => setChunks(chunks.filter((_, k) => k !== i))}
                      aria-label={`Bỏ ${cfg.itemLabel.toLowerCase()} ${i + 1}`}
                      className="btn btn-quiet !p-1.5"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
                <textarea
                  id={`chunk-${i}`}
                  value={chunk}
                  onChange={e => setChunks(chunks.map((c, k) => (k === i ? e.target.value : c)))}
                  rows={7}
                  className="field font-copy"
                  placeholder={i === 0 ? cfg.placeholder : ''}
                />
              </div>
            ))}
          </div>

          {estimate ? (
            <div className="sheet px-5 py-4" style={{ borderLeft: '2px solid var(--warn)' }}>
              <p className="t-label mb-1.5">Xác nhận trước khi đọc</p>
              <p className="text-[0.9375rem] mb-1">
                Sẽ đọc <strong>{estimate.input_chars.toLocaleString('vi-VN')}</strong> ký tự
                {estimate.estimated_cost != null && (
                  <> — ước tính <strong>{formatCost(estimate.estimated_cost)}</strong></>
                )}
              </p>
              <p className="text-[0.875rem] text-ink-2 mb-3">
                Đọc lại đúng tài liệu này lần sau sẽ không mất phí.
              </p>
              <div className="flex flex-wrap gap-2.5">
                <button onClick={handleExtract} disabled={busy} className="btn btn-primary">
                  {busy && <Loader2 className="w-4 h-4 animate-spin" />}
                  {busy ? 'Đang đọc' : 'Đọc ngay'}
                </button>
                <button onClick={() => setEstimate(null)} disabled={busy} className="btn btn-quiet">
                  Để sửa lại tài liệu đã
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap gap-2.5">
                <button onClick={() => setChunks([...chunks, ''])} disabled={busy} className="btn btn-quiet">
                  <Plus className="w-4 h-4" /> Thêm {cfg.itemLabel.toLowerCase()}
                </button>
                <button
                  onClick={handleAskPrice}
                  disabled={busy || filled.length === 0}
                  className="btn btn-primary"
                >
                  {busy && <Loader2 className="w-4 h-4 animate-spin" />}
                  {busy ? 'Đang tính' : 'Đọc và đề xuất'}
                </button>
              </div>

              <p className="mt-3 text-[0.8125rem] text-ink-3">
                Bước đọc dùng AI và có tính phí — sẽ hiện giá để bạn xác nhận trước. Chưa có gì
                được ghi vào kho brand cho tới khi bạn duyệt.
              </p>
            </>
          )}
        </>
      )}

      {/* Duyệt đề xuất */}
      {draft && (
        <div>
          <div className="sheet spot px-5 py-4 mb-6">
            <p className="t-label mb-1">Đề xuất</p>
            <p className="text-[0.9375rem]">
              Chọn phần bạn muốn giữ. Bỏ chọn thì không ghi gì vào file đó.
            </p>
            {draft.usage && (
              <p className="text-[0.8125rem] text-ink-3 mt-2">
                {draft.usage.cached
                  ? 'Lấy lại từ lần đọc trước, không tốn thêm phí.'
                  : `Lần đọc này tốn khoảng ${formatCost(draft.usage.cost_estimate)}.`}
              </p>
            )}
          </div>

          <DraftReview
            draft={draft}
            chosen={chosen}
            setChosen={setChosen}
            takeVoice={takeVoice}
            setTakeVoice={setTakeVoice}
            takeMeta={takeMeta}
            setTakeMeta={setTakeMeta}
          />

          <div className="flex flex-wrap gap-2.5 pt-5 border-t border-rule">
            <button onClick={() => setDraft(null)} disabled={busy} className="btn btn-quiet">
              Quay lại sửa tài liệu
            </button>
            <button onClick={handleApply} disabled={busy || soChon === 0} className="btn btn-primary">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Lưu {soChon} phần đã chọn
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
