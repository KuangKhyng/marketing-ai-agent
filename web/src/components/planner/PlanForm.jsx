import { useState } from 'react';
import PlannerDialog from './PlannerDialog';
import { dateKey, fieldClass } from '../../utils/planner';

export default function PlanForm({ plan, onSave, onClose, busy, error }) {
  const [form, setForm] = useState(() => ({ title: plan?.title || '', brand: plan?.brand || '', objective: plan?.objective || '',
    start_date: plan?.start_date || dateKey(new Date()),
    end_date: plan?.end_date || dateKey(new Date(Date.now() + 27 * 86400000)) }));
  const change = event => setForm({ ...form, [event.target.name]: event.target.value });
  return <PlannerDialog title={plan ? 'Chỉnh sửa kế hoạch' : 'Một kế hoạch, nhiều nội dung'} onClose={onClose} busy={busy}>
    <form className="space-y-4" onSubmit={event => { event.preventDefault(); onSave(form); }}>
      <p className="text-sm text-ink-2">Xác định mục tiêu trước, sau đó chia thành các bài theo tuần và theo kênh.</p>
      <label className="block">Tên kế hoạch<input autoFocus required maxLength={160} name="title" value={form.title} onChange={change} placeholder="Ra mắt bộ sưu tập mùa thu" className={`${fieldClass} mt-1`} /></label>
      <label className="block">Thương hiệu<input maxLength={160} name="brand" value={form.brand} onChange={change} placeholder="Tên thương hiệu để phân biệt các kế hoạch" className={`${fieldClass} mt-1`} /></label>
      <label className="block">Mục tiêu<textarea maxLength={4000} rows={3} name="objective" value={form.objective} onChange={change} placeholder="Bạn muốn khách hàng hiểu, cảm nhận hoặc làm gì?" className={`${fieldClass} mt-1`} /></label>
      <div className="grid grid-cols-2 gap-3">
        <label>Ngày bắt đầu<input type="date" required name="start_date" value={form.start_date} onChange={change} className={`${fieldClass} mt-1`} /></label>
        <label>Ngày kết thúc<input type="date" required min={form.start_date} name="end_date" value={form.end_date} onChange={change} className={`${fieldClass} mt-1`} /></label>
      </div>
      {error && <p role="alert" className="text-fail">{error}</p>}
      <button disabled={busy || !form.title.trim()} className="btn btn-primary w-full">{busy ? 'Đang lưu…' : plan ? 'Lưu thay đổi' : 'Tạo kế hoạch'}</button>
    </form>
  </PlannerDialog>;
}
