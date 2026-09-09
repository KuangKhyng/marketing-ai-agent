import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { libraryAPI } from '../../api/client';
import PlannerDialog from './PlannerDialog';
import { CHANNELS, STAGES, fieldClass, taskPayload, errorMessage } from '../../utils/planner';

export default function TaskForm({ task, plan, onSave, onClose, onGenerate, busy, error }) {
  const [form, setForm] = useState(() => task ? taskPayload(task) : ({ title: '', brief: '', channel: 'facebook', owner: '', due_date: null,
    status: 'idea', snapshot_id: null, piece_index: null, publication_url: null, archived: false }));
  const [library, setLibrary] = useState([]);
  const [snapshot, setSnapshot] = useState(null);
  const [libraryError, setLibraryError] = useState('');
  const [libraryAttempt, setLibraryAttempt] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setLibraryError('');
    libraryAPI.list().then(({ data }) => { if (!cancelled) setLibrary(data); }).catch(error => { if (!cancelled) setLibraryError(errorMessage(error)); });
    return () => { cancelled = true; };
  }, [libraryAttempt]);
  useEffect(() => {
    let cancelled = false;
    setSnapshot(null);
    if (form.snapshot_id) libraryAPI.get(form.snapshot_id).then(({ data }) => {
      if (!cancelled) setSnapshot(data);
    }).catch(error => { if (!cancelled) setLibraryError(errorMessage(error)); });
    return () => { cancelled = true; };
  }, [form.snapshot_id, libraryAttempt]);
  const change = event => setForm({ ...form, [event.target.name]: event.target.value });
  const pieces = snapshot?.campaign?.content?.pieces || [];
  const review = snapshot?.campaign?.review_result;
  return <PlannerDialog title={task ? 'Chi tiết công việc' : 'Thêm ý tưởng nội dung'} onClose={onClose} busy={busy}>
    <form className="space-y-4" onSubmit={event => { event.preventDefault(); onSave(form); }}>
      <label className="block">Tên bài<input autoFocus required maxLength={200} name="title" value={form.title} onChange={change} placeholder="Một thông điệp cụ thể cho một bài" className={`${fieldClass} mt-1`} /></label>
      <div className="grid sm:grid-cols-2 gap-3">
        <label>Kênh<select name="channel" value={form.channel} onChange={event => setForm({ ...form, channel: event.target.value, snapshot_id: null, piece_index: null, status: 'idea' })} className={`${fieldClass} mt-1`}>{Object.entries(CHANNELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
        <label>Trạng thái<select name="status" value={form.status} onChange={change} className={`${fieldClass} mt-1`}>{STAGES.map(stage => <option key={stage.id} value={stage.id}>{stage.label}</option>)}</select></label>
        <label>Ngày đăng dự kiến<input type="date" min={plan.start_date} max={plan.end_date} value={form.due_date || ''} onChange={event => setForm({ ...form, due_date: event.target.value || null })} className={`${fieldClass} mt-1`} /></label>
        <label>Người phụ trách<input name="owner" maxLength={120} value={form.owner} onChange={change} placeholder="Tên người phụ trách" className={`${fieldClass} mt-1`} /></label>
      </div>
      <label className="block">Brief cho bài viết<textarea rows={4} maxLength={8000} name="brief" value={form.brief} onChange={change} placeholder="Thông điệp, đối tượng, CTA và bằng chứng cần dùng…" className={`${fieldClass} mt-1`} /></label>
      <fieldset className="border border-rule rounded-xl p-4 space-y-3">
        <legend className="px-2 text-sm">Gắn nội dung từ thư viện</legend>
        <label className="block text-sm">Bản lưu<select value={form.snapshot_id || ''} onChange={event => setForm({ ...form, snapshot_id: event.target.value || null, piece_index: null, status: 'review' })} className={`${fieldClass} mt-1`}>
          <option value="">Chưa gắn nội dung</option>{library.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select></label>
        {form.snapshot_id && <label className="block text-sm">Bài trong bản lưu<select required value={form.piece_index ?? ''} onChange={event => setForm({ ...form, piece_index: Number(event.target.value), status: 'review' })} className={`${fieldClass} mt-1`}>
          <option value="" disabled>Chọn bài đúng kênh</option>{pieces.map((piece, index) => piece.channel === form.channel && <option key={index} value={index}>Bài {index + 1} · {piece.deliverable} · {piece.hook || piece.body?.slice(0, 60)}</option>)}
        </select></label>}
        {snapshot && <p className="text-sm text-ink-2">{review?.overall_passed && !review?.review_unavailable ? 'Đã đạt kiểm duyệt AI.' : 'Bản này chưa đạt kiểm duyệt, chưa thể chuyển sang Sẵn sàng.'} <Link className="underline" to={`/library/${snapshot.id}`} target="_blank" rel="noopener noreferrer">Đọc bản lưu (tab mới)</Link></p>}
        {libraryError && <p role="alert" className="text-sm text-fail">{libraryError} <button type="button" className="underline" onClick={() => setLibraryAttempt(value => value + 1)}>Tải lại thư viện</button></p>}
        {!library.length && !libraryError && <p className="text-sm text-ink-2">Sau khi tạo và kiểm duyệt nội dung, lưu vào thư viện rồi quay lại gắn bài.</p>}
      </fieldset>
      <label className="block">URL bài đã đăng<input type="url" value={form.publication_url || ''} required={form.status === 'published'} onChange={event => setForm({ ...form, publication_url: event.target.value || null })} placeholder="https://…" className={`${fieldClass} mt-1`} /></label>
      <p className="text-xs text-ink-2">Ngày dự kiến không tự đăng bài. “Đã đăng” là xác nhận thủ công, cần bài đã sẵn sàng và URL xuất bản.</p>
      {task && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.archived} onChange={event => setForm({ ...form, archived: event.target.checked })} />Ẩn khỏi bảng và lịch (có thể khôi phục)</label>}
      {error && <p role="alert" className="text-fail">{error}</p>}
      {task?.status === 'published' && <p className="text-sm text-ink-2">Bài này đã được ghi nhận xuất bản. Để viết phương án khác, tạo công việc mới và giữ bản gốc trong lịch.</p>}
      <div className="flex flex-wrap gap-3">
        <button disabled={busy || !form.title.trim()} className="btn btn-primary">{busy ? 'Đang lưu…' : 'Lưu công việc'}</button>
        <button type="button" disabled={busy || !form.title.trim() || task?.status === 'published' || form.archived} onClick={event => { if (event.currentTarget.form.reportValidity()) onGenerate(form); }} className="btn btn-default">Lưu và chuẩn bị brief AI</button>
      </div>
      <p className="text-xs text-ink-2">Chuẩn bị brief chỉ mở màn hình tạo nội dung. AI chỉ chạy khi bạn bấm bắt đầu tại đó.</p>
    </form>
  </PlannerDialog>;
}
