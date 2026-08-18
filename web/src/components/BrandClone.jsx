import { useState } from 'react';
import { brandsAPI } from '../api/client';
import { Loader2 } from 'lucide-react';
import { slugify } from '../utils/slug';

/*
 * Nhân bản một brand có sẵn.
 *
 * Dành cho trường hợp làm brand cùng ngành khác sản phẩm: giữ giọng, khung
 * bài, chân dung khách và ràng buộc pháp lý, chỉ thay phần sản phẩm.
 *
 * Không tốn lượt gọi API nào — chỉ chép file.
 */
export default function BrandClone({ brands, onCreated, showToast }) {
  const [sourceId, setSourceId] = useState(brands[0]?.id || '');
  const [name, setName] = useState('');
  const [id, setId] = useState('');
  const [idTouched, setIdTouched] = useState(false);
  const [description, setDescription] = useState('');
  const [includeProducts, setIncludeProducts] = useState(false);
  const [busy, setBusy] = useState(false);

  const source = brands.find(b => b.id === sourceId);

  const handleName = (value) => {
    setName(value);
    if (!idTouched) setId(slugify(value));
  };

  const handleClone = async () => {
    setBusy(true);
    try {
      const { data } = await brandsAPI.clone({
        source_id: sourceId,
        id: id.trim(),
        name: name.trim(),
        description: description.trim(),
        icon: source?.icon || '📦',
        color: source?.color || '#6c5ce7',
        include_products: includeProducts,
      });
      onCreated(data.id);
    } catch (err) {
      showToast(
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        'Không nhân bản được.'
      );
    } finally {
      setBusy(false);
    }
  };

  if (brands.length === 0) {
    return (
      <p className="text-[0.9375rem] text-ink-2 py-4">
        Chưa có brand nào để nhân bản. Tạo brand đầu tiên từ tài liệu đã.
      </p>
    );
  }

  return (
    <div>
      <p className="t-lede mb-6">
        Giữ giọng văn, khung bài, chân dung khách và ràng buộc nội dung của brand cũ. Sản phẩm
        thì làm lại từ đầu — đó thường là lý do người ta nhân bản.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-5 mb-5">
        <div className="md:col-span-2">
          <label htmlFor="cl-source" className="t-label block mb-2">Nhân bản từ</label>
          <select
            id="cl-source"
            value={sourceId}
            onChange={e => setSourceId(e.target.value)}
            className="field"
          >
            {brands.map(b => (
              <option key={b.id} value={b.id}>
                {b.icon} {b.name} — {b.completeness?.score ?? 0}% đầy
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="cl-name" className="t-label block mb-2">Tên brand mới</label>
          <input
            id="cl-name"
            value={name}
            onChange={e => handleName(e.target.value)}
            placeholder="Phong Thuỷ Online"
            className="field"
          />
        </div>

        <div>
          <label htmlFor="cl-id" className="t-label block mb-2">Mã brand</label>
          <input
            id="cl-id"
            value={id}
            onChange={e => { setIdTouched(true); setId(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, '_')); }}
            placeholder="phong_thuy_online"
            className="field font-data"
          />
          <p className="text-[0.8125rem] text-ink-3 mt-1.5">
            <strong>Không đổi được sau khi tạo.</strong>
          </p>
        </div>

        <div className="md:col-span-2">
          <label htmlFor="cl-desc" className="t-label block mb-2">Mô tả ngắn</label>
          <input
            id="cl-desc"
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Dịch vụ xem phong thuỷ nhà ở"
            className="field"
          />
        </div>
      </div>

      <label className="sheet flex items-start gap-3 px-5 py-3.5 cursor-pointer mb-6">
        <input
          type="checkbox"
          checked={includeProducts}
          onChange={e => setIncludeProducts(e.target.checked)}
          className="mt-1"
        />
        <span>
          <span className="text-[0.9375rem] font-medium">Chép cả sản phẩm của brand cũ</span>
          <p className="text-[0.875rem] text-ink-2 mt-1">
            Mặc định không chép. Giữ lại thì bài viết sẽ nói về hàng của brand cũ, mà phần chấm
            chất lượng coi kho brand là nguồn sự thật nên sẽ không bắt được lỗi đó.
          </p>
        </span>
      </label>

      <div className="pt-5 border-t border-rule">
        <button
          onClick={handleClone}
          disabled={busy || !id.trim() || !name.trim() || !sourceId}
          className="btn btn-primary"
        >
          {busy && <Loader2 className="w-4 h-4 animate-spin" />}
          Nhân bản
        </button>
        <p className="mt-2.5 text-[0.8125rem] text-ink-3">
          Chỉ chép file, không gọi AI nên không tốn phí.
        </p>
      </div>
    </div>
  );
}
