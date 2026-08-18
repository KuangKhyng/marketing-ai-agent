import { useState } from 'react';
import { FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/*
 * Duyệt bản đề xuất do hệ thống đọc ra từ tài liệu.
 *
 * Dùng chung cho hai luồng:
 *   - tạo brand mới từ tài liệu (BrandCreate)
 *   - nạp thêm cho brand đã có   (BrandBootstrap)
 *
 * Tách ra để hai luồng không trôi mỗi nơi một kiểu — chúng phải hiện cùng một
 * thứ theo cùng một cách, vì đều là quyết định "ghi gì vào nguồn sự thật".
 */
export default function DraftReview({
  draft,
  chosen,
  setChosen,
  takeVoice,
  setTakeVoice,
  takeMeta,
  setTakeMeta,
}) {
  const [compare, setCompare] = useState({});
  const hasMeta = Object.keys(draft.brand_meta || {}).length > 0;

  return (
    <div className="space-y-3">
      {draft.notes?.length > 0 && (
        <div className="sheet px-5 py-4" style={{ borderLeft: '2px solid var(--warn)' }}>
          <p className="t-label mb-2">Tài liệu chưa nói tới</p>
          {draft.notes.map((n, i) => (
            <p key={i} className="text-[0.875rem] text-ink-2 leading-relaxed">{n}</p>
          ))}
          <p className="text-[0.8125rem] text-ink-3 mt-2">
            Những chỗ này hệ thống cố tình để trống thay vì đoán. Bạn bổ sung sau ở tab Tài liệu.
          </p>
        </div>
      )}

      {draft.files.map(f => (
        <div key={f.path} className="sheet">
          <label className="flex items-start gap-3 px-5 py-3.5 cursor-pointer">
            <input
              type="checkbox"
              checked={Boolean(chosen[f.path])}
              onChange={e => setChosen({ ...chosen, [f.path]: e.target.checked })}
              className="mt-1"
            />
            <span className="min-w-0 flex-1 flex items-center gap-2 flex-wrap">
              <FileText className="w-3.5 h-3.5 shrink-0" />
              <span className="text-[0.9375rem] font-medium">{f.label || f.path}</span>
              <span className="font-data text-[0.75rem] text-ink-3">{f.path}</span>
              {f.exists && <span className="tag tag-warn">Ghi đè nội dung cũ</span>}
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
              {draft.voice_profile.tone?.formality},{' '}
              {draft.voice_profile.anti_ai_rules?.length || 0} quy tắc tránh giọng AI
            </p>
          </span>
        </label>
      )}

      {hasMeta && (
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
  );
}
