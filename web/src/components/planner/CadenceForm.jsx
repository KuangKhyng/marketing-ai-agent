import { useState } from 'react';
import PlannerDialog from './PlannerDialog';
import { CHANNELS } from '../../utils/planner';

export default function CadenceForm({ onSave, onClose, busy, error, plan }) {
  const [channels, setChannels] = useState(['facebook']);
  const [weekdays, setWeekdays] = useState([0, 2, 4]);
  const toggle = (values, value, set) => set(values.includes(value) ? values.filter(item => item !== value) : [...values, value]);
  return <PlannerDialog title="Dựng lịch nội dung mẫu" onClose={onClose} busy={busy}>
    <form className="space-y-5" onSubmit={event => { event.preventDefault(); onSave({ channels, weekdays }); }}>
      <p className="text-ink-2 text-sm">Tạo ý tưởng từ {plan.start_date} đến {plan.end_date}, luân phiên kiến thức, câu chuyện thương hiệu và sản phẩm. Bạn chỉnh brief trước khi viết. Không gọi AI.</p>
      <fieldset><legend className="mb-2">Kênh nội dung</legend><div className="flex flex-wrap gap-4">{Object.entries(CHANNELS).map(([id, label]) => <label key={id} className="flex gap-2 items-center"><input type="checkbox" checked={channels.includes(id)} onChange={() => toggle(channels, id, setChannels)} />{label}</label>)}</div></fieldset>
      <fieldset><legend className="mb-2">Ngày trong tuần</legend><div className="flex flex-wrap gap-3">{['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'CN'].map((label, id) => <label key={id} className="flex gap-2 items-center"><input type="checkbox" checked={weekdays.includes(id)} onChange={() => toggle(weekdays, id, setWeekdays)} />{label}</label>)}</div></fieldset>
      <p className="text-sm text-ink-2">Bỏ qua ngày/kênh đã có bài; không ghi đè ý tưởng hiện tại.</p>
      {error && <p role="alert" className="text-fail">{error}</p>}
      <button disabled={busy || !channels.length || !weekdays.length} className="btn btn-primary w-full">{busy ? 'Đang dựng lịch…' : 'Tạo các ý tưởng theo lịch'}</button>
    </form>
  </PlannerDialog>;
}
