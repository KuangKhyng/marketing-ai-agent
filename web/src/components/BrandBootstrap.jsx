import { useState } from 'react';
import { brandsAPI } from '../api/client';
import { Loader2, Plus, X, FileText, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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
  },
  brand: {
    label: 'Tài liệu brand',
    lede: 'Dán hồ sơ công ty, mô tả sản phẩm, ghi chú về khách hàng. Hệ thống sắp xếp thành bộ khung brand.',
    itemLabel: 'Tài liệu',
    placeholder:
      'Dán tài liệu về brand: bạn bán gì, cho ai, điều gì khiến khách chọn bạn.\n\nCó gì dán nấy — thiếu chỗ nào hệ thống sẽ nói ra chỗ đó.',
    call: (brandId, chunks) => brandsAPI.bootstrapBrand(brandId, chunks),
  },
};

export default function BrandBootstrap({ brandId, onApplied, showToast }) {
  const [stage, setStage] = useState('voice');
  const [chunks, setChunks] = useState(['']);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState(null);
  const [chosen, setChosen] = useState({});      // path -> bool
  const [takeVoice, setTakeVoice] = useState(true);
  const [takeMeta, setTakeMeta] = useState(true);
  const [compare, setCompare] = useState({});    // path -> bool

  const cfg = STAGES[stage];
  const filled = chunks.filter(c => c.trim().length > 0);

  const switchStage = (next) => {
    setStage(next);
    setChunks(['']);
    setDraft(null);
  };

  const handleExtract = async () => {
    setBusy(true);
    setDraft(null);
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

  const soChon =
    Object.values(chosen).filter(Boolean).length +
    (takeVoice && draft?.voice_profile ? 1 : 0) +
    (takeMeta && Object.keys(draft?.brand_meta || {}).length ? 1 : 0);

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

          <div className="flex flex-wrap gap-2.5">
            <button onClick={() => setChunks([...chunks, ''])} disabled={busy} className="btn btn-quiet">
              <Plus className="w-4 h-4" /> Thêm {cfg.itemLabel.toLowerCase()}
            </button>
            <button
              onClick={handleExtract}
              disabled={busy || filled.length === 0}
              className="btn btn-primary"
            >
              {busy && <Loader2 className="w-4 h-4 animate-spin" />}
              {busy ? 'Đang đọc' : 'Đọc và đề xuất'}
            </button>
          </div>

          {busy && (
            <p className="mt-3 text-[0.8125rem] text-ink-3">
              Thường mất 20–40 giây. Chưa có gì được ghi vào kho brand cho tới khi bạn duyệt.
            </p>
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
          </div>

          {draft.notes?.length > 0 && (
            <div className="sheet px-5 py-4 mb-6" style={{ borderLeft: '2px solid var(--warn)' }}>
              <p className="t-label mb-2">Tài liệu chưa nói tới</p>
              {draft.notes.map((n, i) => (
                <p key={i} className="text-[0.875rem] text-ink-2 leading-relaxed">{n}</p>
              ))}
              <p className="text-[0.8125rem] text-ink-3 mt-2">
                Những chỗ này hệ thống cố tình để trống thay vì đoán. Bạn tự điền sau ở tab Tài liệu.
              </p>
            </div>
          )}

          <div className="space-y-3 mb-6">
            {draft.files.map(f => (
              <div key={f.path} className="sheet">
                <label className="flex items-start gap-3 px-5 py-3.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={Boolean(chosen[f.path])}
                    onChange={e => setChosen({ ...chosen, [f.path]: e.target.checked })}
                    className="mt-1"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2 flex-wrap">
                      <FileText className="w-3.5 h-3.5 shrink-0" />
                      <span className="text-[0.9375rem] font-medium">{f.label || f.path}</span>
                      <span className="font-data text-[0.75rem] text-ink-3">{f.path}</span>
                      {f.exists && <span className="tag tag-warn">Ghi đè nội dung cũ</span>}
                    </span>
                  </span>
                </label>

                <div className="px-5 pb-4">
                  {f.exists && (
                    <button
                      onClick={() => setCompare({ ...compare, [f.path]: !compare[f.path] })}
                      className="btn btn-quiet !py-1.5 !px-2.5 !text-[0.75rem] mb-3"
                    >
                      {compare[f.path] ? 'Xem bản đề xuất' : 'So với bản đang có'}
                    </button>
                  )}
                  <div className="md !text-[0.875rem] max-h-72 overflow-y-auto border-t border-rule pt-3">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {compare[f.path] ? f.current || '_(trống)_' : f.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}

            {draft.voice_profile && (
              <label className="sheet flex items-start gap-3 px-5 py-3.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={takeVoice}
                  onChange={e => setTakeVoice(e.target.checked)}
                  className="mt-1"
                />
                <span>
                  <span className="text-[0.9375rem] font-medium">Hồ sơ giọng</span>
                  <span className="font-data text-[0.75rem] text-ink-3 ml-2">voice_profile.json</span>
                  <p className="text-[0.875rem] text-ink-2 mt-1">
                    Tone {draft.voice_profile.tone?.primary}, mức trang trọng{' '}
                    {draft.voice_profile.tone?.formality}, {draft.voice_profile.anti_ai_rules?.length || 0} quy tắc
                    tránh giọng AI
                  </p>
                </span>
              </label>
            )}

            {Object.keys(draft.brand_meta || {}).length > 0 && (
              <label className="sheet flex items-start gap-3 px-5 py-3.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={takeMeta}
                  onChange={e => setTakeMeta(e.target.checked)}
                  className="mt-1"
                />
                <span>
                  <span className="text-[0.9375rem] font-medium">Ràng buộc nội dung</span>
                  <span className="font-data text-[0.75rem] text-ink-3 ml-2">brand.json</span>
                  {draft.brand_meta.forbidden_claims?.length > 0 && (
                    <p className="text-[0.875rem] text-ink-2 mt-1">
                      Không được nói: {draft.brand_meta.forbidden_claims.join(' · ')}
                    </p>
                  )}
                  {draft.brand_meta.mandatory_terms?.length > 0 && (
                    <p className="text-[0.875rem] text-ink-2 mt-1">
                      Bắt buộc có: {draft.brand_meta.mandatory_terms.join(' · ')}
                    </p>
                  )}
                </span>
              </label>
            )}
          </div>

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
