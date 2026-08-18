import { useState } from 'react';
import { brandsAPI } from '../api/client';
import { Loader2, Plus, X, ArrowLeft } from 'lucide-react';
import DraftReview from './DraftReview';
import { countChosen } from '../utils/draft';

/*
 * Tạo brand TỪ tài liệu.
 *
 * Tài liệu là điểm xuất phát, không phải thứ nhét vào sau: dán bài đã đăng và
 * hồ sơ brand, hệ thống đọc rồi đề xuất cả tên lẫn mã brand lẫn toàn bộ nội
 * dung. Người dùng sửa và bỏ bớt, rồi mới tạo.
 *
 * Vẫn giữ lối thoát "tạo brand trống" cho ai chưa có tài liệu gì.
 */

const BRAND_ICONS = ['📦', '☕', '💅', '🏠', '🎵', '📱', '🎨', '🍕', '✦', '🌿', '💎', '🔥'];

const CHECK_LABEL = {
  identity: 'Nhận diện',
  tone: 'Giọng văn',
  product: 'Sản phẩm',
  audience: 'Khách hàng',
};

export default function BrandCreate({ onCreated, onCancel, onEmptyBrand, showToast }) {
  const [posts, setPosts] = useState(['']);
  const [docs, setDocs] = useState(['']);
  const [nameHint, setNameHint] = useState('');

  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(null);

  // Bước duyệt — sửa được trước khi tạo
  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [icon, setIcon] = useState('📦');
  const [chosen, setChosen] = useState({});
  const [takeVoice, setTakeVoice] = useState(true);
  const [takeMeta, setTakeMeta] = useState(true);

  const coTaiLieu = [...posts, ...docs].some(c => c.trim());

  const handleRead = async () => {
    setBusy(true);
    try {
      const { data } = await brandsAPI.bootstrapPreview({
        samples: posts.filter(p => p.trim()),
        documents: docs.filter(d => d.trim()),
        name_hint: nameHint.trim(),
      });
      setPreview(data);
      setId(data.identity.suggested_id);
      setName(data.identity.name);
      setDescription(data.identity.description);
      setChosen(Object.fromEntries(data.draft.files.map(f => [f.path, true])));
      setTakeVoice(Boolean(data.draft.voice_profile));
      setTakeMeta(Object.keys(data.draft.brand_meta || {}).length > 0);
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

  const handleCreate = async () => {
    setBusy(true);
    try {
      // Giữ nguyên văn tài liệu để sau này đọc lại được bằng prompt tốt hơn
      const sources = {};
      posts.filter(p => p.trim()).forEach((p, i) => { sources[`bai_dang_${i + 1}`] = p; });
      docs.filter(d => d.trim()).forEach((d, i) => { sources[`tai_lieu_${i + 1}`] = d; });

      const { data } = await brandsAPI.bootstrapCreate({
        id: id.trim(),
        name: name.trim(),
        description: description.trim(),
        icon,
        files: preview.draft.files.filter(f => chosen[f.path]),
        voice_profile: takeVoice ? preview.draft.voice_profile : null,
        brand_meta: takeMeta ? preview.draft.brand_meta : null,
        sources,
      });
      onCreated(data.brand_id);
    } catch (err) {
      showToast(
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        'Không tạo được brand.'
      );
    } finally {
      setBusy(false);
    }
  };

  /* ---------------- Bước 1: dán tài liệu ---------------- */

  if (!preview) {
    return (
      <div className="sheet p-6 rise relative">
        <button onClick={onCancel} aria-label="Đóng" className="btn btn-quiet !p-2 absolute top-3 right-3">
          <X className="w-4 h-4" />
        </button>

        <h2 className="t-section mb-2">Brand mới</h2>
        <p className="t-lede mb-6">
          Dán những gì bạn đã có. Hệ thống đọc rồi dựng sẵn nhận diện, giọng văn, sản phẩm và
          chân dung khách — bạn chỉ việc sửa lại cho đúng.
        </p>

        <PasteGroup
          label="Bài bạn đã từng đăng"
          hint="Để rút ra giọng văn và khung bài quen thuộc. 3–5 bài là đủ."
          items={posts}
          setItems={setPosts}
          itemLabel="Bài"
          placeholder="Dán nguyên văn một bài đã đăng, kể cả emoji và hashtag."
          disabled={busy}
        />

        <PasteGroup
          label="Tài liệu về brand"
          hint="Hồ sơ công ty, mô tả sản phẩm, ghi chú về khách hàng. Có gì dán nấy."
          items={docs}
          setItems={setDocs}
          itemLabel="Tài liệu"
          placeholder="Bạn bán gì, cho ai, điều gì khiến khách chọn bạn thay vì chỗ khác."
          disabled={busy}
        />

        <div className="mb-6">
          <label htmlFor="name-hint" className="t-label block mb-2">
            Tên brand <span className="text-ink-3 font-normal">— để trống thì hệ thống tự đọc từ tài liệu</span>
          </label>
          <input
            id="name-hint"
            value={nameHint}
            onChange={e => setNameHint(e.target.value)}
            placeholder="Tử Vi Online"
            className="field"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2.5 pt-5 border-t border-rule">
          <button onClick={handleRead} disabled={busy || !coTaiLieu} className="btn btn-primary">
            {busy && <Loader2 className="w-4 h-4 animate-spin" />}
            {busy ? 'Đang đọc tài liệu' : 'Đọc và dựng brand'}
          </button>
          <button onClick={onEmptyBrand} disabled={busy} className="btn btn-quiet">
            Tôi chưa có tài liệu, tạo brand trống
          </button>
        </div>

        <p className="mt-3 text-[0.8125rem] text-ink-3">
          Bước đọc dùng AI nên mất khoảng 30–60 giây và có tính phí. Chưa có gì được tạo cho tới
          khi bạn duyệt ở bước sau.
        </p>
      </div>
    );
  }

  /* ---------------- Bước 2: duyệt rồi tạo ---------------- */

  const soChon = countChosen(preview.draft, chosen, takeVoice, takeMeta);
  const checks = preview.completeness?.checks || {};
  const conThieu = Object.entries(checks).filter(([, v]) => !v).map(([k]) => CHECK_LABEL[k] || k);

  return (
    <div className="sheet p-6 rise">
      <div className="flex items-start justify-between gap-4 flex-wrap mb-6">
        <div>
          <h2 className="t-section mb-1">Kiểm lại trước khi tạo</h2>
          <p className="t-lede">Sửa chỗ nào chưa đúng, bỏ chọn phần bạn không muốn giữ.</p>
        </div>
        <button onClick={() => setPreview(null)} disabled={busy} className="btn btn-quiet shrink-0">
          <ArrowLeft className="w-4 h-4" /> Sửa tài liệu
        </button>
      </div>

      {/* Brand sẽ đầy tới đâu */}
      <div className="sheet spot px-5 py-4 mb-6">
        <div className="flex items-baseline justify-between gap-4 mb-2">
          <p className="t-label">Brand này sẽ bắt đầu ở mức</p>
          <span className="font-data text-[0.9375rem] num">{preview.completeness?.score ?? 0}%</span>
        </div>
        <div className="relative h-[6px] rounded-full overflow-hidden mb-2.5"
             style={{ background: 'rgba(255,255,255,.06)' }}>
          <div className="absolute inset-y-0 left-0 rounded-full"
               style={{ width: `${preview.completeness?.score ?? 0}%`, background: 'var(--pass)' }} />
        </div>
        <p className="text-[0.875rem] text-ink-2">
          {conThieu.length === 0
            ? 'Đủ cả bốn phần. Chạy campaign được ngay.'
            : `Còn thiếu: ${conThieu.join(', ')}. Bổ sung sau ở tab Nạp liệu cũng được.`}
        </p>
      </div>

      {/* Danh tính — sửa được */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5 mb-5">
        <div>
          <label htmlFor="c-name" className="t-label block mb-2">Tên hiển thị</label>
          <input id="c-name" value={name} onChange={e => setName(e.target.value)} className="field" />
        </div>
        <div>
          <label htmlFor="c-id" className="t-label block mb-2">Mã brand</label>
          <input
            id="c-id"
            value={id}
            onChange={e => setId(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, '_'))}
            className="field font-data"
          />
          <p className="text-[0.8125rem] text-ink-3 mt-1.5">
            Dùng làm tên thư mục. <strong>Không đổi được sau khi tạo.</strong>
          </p>
          {preview.identity?.id_taken && id === preview.identity.suggested_id && (
            <p className="text-[0.8125rem] mt-1.5" style={{ color: 'var(--fail)' }}>
              Mã này đã có brand khác dùng. Đổi thành mã khác.
            </p>
          )}
        </div>
        <div className="md:col-span-2">
          <label htmlFor="c-desc" className="t-label block mb-2">Mô tả ngắn</label>
          <input
            id="c-desc"
            value={description}
            onChange={e => setDescription(e.target.value)}
            className="field"
          />
        </div>
      </div>

      <div className="mb-6">
        <p className="t-label mb-2">Biểu tượng</p>
        <div className="flex gap-1 flex-wrap max-w-[320px]">
          {BRAND_ICONS.map(i => (
            <button
              key={i}
              onClick={() => setIcon(i)}
              aria-label={`Chọn ${i}`}
              className={`w-9 h-9 rounded-[3px] text-[1.05rem] transition-colors ${
                icon === i ? 'bg-cham' : 'bg-inset hover:bg-sheet'
              }`}
            >
              {i}
            </button>
          ))}
        </div>
      </div>

      <p className="t-label mb-3">Nội dung sẽ ghi vào kho</p>
      <DraftReview
        draft={preview.draft}
        chosen={chosen}
        setChosen={setChosen}
        takeVoice={takeVoice}
        setTakeVoice={setTakeVoice}
        takeMeta={takeMeta}
        setTakeMeta={setTakeMeta}
      />

      <div className="flex flex-wrap gap-2.5 pt-6 mt-6 border-t border-rule">
        <button onClick={onCancel} disabled={busy} className="btn btn-quiet">Huỷ</button>
        <button
          onClick={handleCreate}
          disabled={busy || !id.trim() || !name.trim()}
          className="btn btn-primary"
        >
          {busy && <Loader2 className="w-4 h-4 animate-spin" />}
          Tạo brand với {soChon} phần
        </button>
      </div>
    </div>
  );
}

function PasteGroup({ label, hint, items, setItems, itemLabel, placeholder, disabled }) {
  return (
    <section className="mb-6">
      <p className="t-label mb-1">{label}</p>
      <p className="text-[0.8125rem] text-ink-3 mb-3">{hint}</p>

      <div className="space-y-3">
        {items.map((item, i) => (
          <div key={i}>
            {items.length > 1 && (
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[0.8125rem] text-ink-3">{itemLabel} {i + 1}</span>
                <button
                  onClick={() => setItems(items.filter((_, k) => k !== i))}
                  aria-label={`Bỏ ${itemLabel.toLowerCase()} ${i + 1}`}
                  className="btn btn-quiet !p-1.5"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
            <textarea
              value={item}
              onChange={e => setItems(items.map((c, k) => (k === i ? e.target.value : c)))}
              rows={5}
              disabled={disabled}
              className="field font-copy"
              placeholder={i === 0 ? placeholder : ''}
            />
          </div>
        ))}
      </div>

      <button onClick={() => setItems([...items, ''])} disabled={disabled} className="btn btn-quiet mt-2.5">
        <Plus className="w-4 h-4" /> Thêm {itemLabel.toLowerCase()}
      </button>
    </section>
  );
}
