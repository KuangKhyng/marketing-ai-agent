import { useState } from 'react';
import { Link } from 'react-router-dom';
import { BookmarkPlus } from 'lucide-react';
import { libraryAPI } from '../api/client';

export default function SaveCampaign({ runId }) {
  const [title, setTitle] = useState('');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(null);
  const [error, setError] = useState('');
  async function save(event) {
    event.preventDefault();
    if (saving || !title.trim()) return;
    setSaving(true);
    setSaved(null);
    setError('');
    try {
      const { data } = await libraryAPI.save(runId, title.trim());
      setSaved(data.id);
    } catch (failure) {
      const detail = failure.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : detail?.message || 'Chưa lưu được chiến dịch. Vui lòng thử lại.');
    } finally { setSaving(false); }
  }
  return <section className="sheet p-5 mb-6 space-y-3" aria-label="Lưu vào thư viện">
    <div className="flex items-center gap-2 font-medium"><BookmarkPlus size={18} /> Giữ lại phiên bản này</div>
    <p className="text-sm text-ink-2">Lưu nội dung và kết quả kiểm duyệt để đọc lại sau khi phiên hết hạn. Không gọi AI.</p>
    <form onSubmit={save} className="flex flex-wrap items-end gap-3">
      <div className="flex-1 min-w-0">
        <label htmlFor="snapshot-title" className="block text-sm mb-1">Tên bản lưu</label>
        <input id="snapshot-title" required maxLength={160} value={title} disabled={saving}
          onChange={event => { setTitle(event.target.value); setSaved(null); }}
          placeholder="Ví dụ: Ra mắt sản phẩm · phương án A"
          className="w-full border border-rule rounded-lg bg-transparent p-2.5" />
      </div>
      <button disabled={saving || !title.trim()} className="btn btn-default">{saving ? 'Đang lưu…' : 'Lưu phiên bản'}</button>
    </form>
    {error && <p role="alert" className="text-sm">{error}</p>}
    {saved && <p role="status" className="text-sm">Đã lưu. <Link to={`/library/${saved}`} className="underline">Xem bản lưu</Link></p>}
  </section>;
}
