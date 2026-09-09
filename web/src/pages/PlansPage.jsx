import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CalendarDays, Columns3, Download, Plus, RefreshCw, Sparkles } from 'lucide-react';
import { plansAPI } from '../api/client';
import PlanForm from '../components/planner/PlanForm';
import CadenceForm from '../components/planner/CadenceForm';
import TaskForm from '../components/planner/TaskForm';
import { CHANNELS, STAGES, dateKey, monthDays, errorMessage, fieldClass, downloadBlob } from '../utils/planner';

function PlanIndex() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState(null);
  const [query, setQuery] = useState('');
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setError('');
    plansAPI.list().then(({ data }) => { if (!cancelled) setPlans(data); }).catch(error => { if (!cancelled) setError(errorMessage(error)); });
    return () => { cancelled = true; };
  }, [attempt]);
  async function create(form) {
    setBusy(true);
    setFormError('');
    try { const { data } = await plansAPI.create(form); navigate(`/plans/${data.id}`); }
    catch (error) { setFormError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  const filtered = plans?.filter(plan => `${plan.title} ${plan.brand}`.toLocaleLowerCase('vi').includes(query.toLocaleLowerCase('vi'))) || [];
  return <div className="space-y-8">
    <header className="flex flex-wrap gap-5 justify-between items-end">
      <div><p className="t-label mb-3">Từ chiến lược đến lịch đăng</p><h1 className="t-page">Kế hoạch nội dung</h1><p className="t-lede mt-3 max-w-xl">Một nơi để tổ chức ý tưởng, phối hợp công việc và theo dõi từng bài đến lúc xuất bản.</p></div>
      <button className="btn btn-primary" onClick={() => { setFormError(''); setCreating(true); }}><Plus size={18} />Kế hoạch mới</button>
    </header>
    {error && <div role="alert" className="sheet p-5">{error} <button className="btn btn-default ml-3" onClick={() => setAttempt(value => value + 1)}>Thử lại</button></div>}
    {!plans && !error && <p role="status">Đang tải kế hoạch…</p>}
    {plans && <>
      <div className="grid grid-cols-3 gap-3">{[['Kế hoạch', plans.length], ['Bài đang tổ chức', plans.reduce((sum, plan) => sum + plan.task_count, 0)], ['Đã đăng', plans.reduce((sum, plan) => sum + plan.published_count, 0)]].map(([label, count]) => <div key={label} className="sheet p-4"><p className="text-3xl font-light">{count}</p><p className="text-sm text-ink-2 mt-1">{label}</p></div>)}</div>
      <label className="block max-w-lg text-sm">Tìm kế hoạch hoặc thương hiệu<input type="search" value={query} onChange={event => setQuery(event.target.value)} className={`${fieldClass} mt-2`} placeholder="Ví dụ: Mùa thu, Cà phê…" /></label>
      {!plans.length ? <section className="sheet p-8 md:p-12 space-y-5"><CalendarDays size={32} className="text-cham" /><h2 className="text-2xl">Bắt đầu với bốn tuần tiếp theo</h2><p className="text-ink-2 max-w-xl">Đặt mục tiêu, chọn nhịp đăng và dựng lịch ý tưởng. Sau đó viết nội dung, gắn bản đã duyệt và theo dõi tiến độ trên cùng một bảng.</p><button className="btn btn-default" onClick={() => setCreating(true)}>Lập kế hoạch đầu tiên</button></section>
        : !filtered.length ? <p role="status">Không có kế hoạch phù hợp.</p> : <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">{filtered.map(plan => <Link key={plan.id} to={`/plans/${plan.id}`} className="sheet p-6 block hover:border-cham transition-colors">
          <p className="t-label mb-3">{plan.brand || 'Chưa đặt thương hiệu'}</p><h2 className="text-xl font-medium break-words">{plan.title}</h2><p className="text-sm text-ink-2 line-clamp-2 mt-2 min-h-10">{plan.objective || 'Bổ sung mục tiêu cho kế hoạch.'}</p>
          <p className="text-xs text-ink-2 mt-5">{plan.start_date} → {plan.end_date}</p><progress aria-label={`Tiến độ ${plan.title}`} value={plan.published_count} max={plan.task_count || 1} className="planner-progress w-full h-1.5 mt-4" /><p className="text-sm mt-2">{plan.published_count}/{plan.task_count} bài đã đăng</p>
        </Link>)}</div>}
    </>}
    {creating && <PlanForm onSave={create} onClose={() => setCreating(false)} busy={busy} error={formError} />}
  </div>;
}

function TaskCard({ task, onOpen, compact = false }) {
  const late = task.due_date && task.due_date < dateKey(new Date()) && task.status !== 'published' && !task.archived;
  const stage = STAGES.find(item => item.id === task.status);
  return <button onClick={() => onOpen(task)} className={`planner-card w-full text-left rounded-xl border border-rule bg-sheet hover:border-cham transition-colors ${compact ? 'p-2' : 'p-4'}`}>
    <div className="flex justify-between gap-2 text-xs text-ink-2"><span>{CHANNELS[task.channel]}</span>{task.snapshot_id && <span title="Đã gắn nội dung">↗ Bản lưu</span>}</div>
    <p className={`font-medium break-words mt-2 ${compact ? 'text-xs line-clamp-2' : 'text-sm'}`}>{task.title}</p>
    {compact && <p className="text-[10px] mt-1" style={{ color: stage.color }}>{stage.label}</p>}
    {!compact && <><p className="text-xs text-ink-2 line-clamp-2 mt-2">{task.brief || 'Chưa có brief'}</p><div className="flex flex-wrap gap-2 justify-between mt-4 text-xs"><span>{task.owner || 'Chưa phân công'}</span><span className={late ? 'text-fail' : 'text-ink-2'}>{late ? 'Quá hạn · ' : ''}{task.due_date || 'Chưa xếp lịch'}</span></div></>}
  </button>;
}

function PlanWorkspace({ planId }) {
  const navigate = useNavigate();
  const [plan, setPlan] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [view, setView] = useState('board');
  const [month, setMonth] = useState('');
  const [query, setQuery] = useState('');
  const [channel, setChannel] = useState('');
  const [showArchived, setShowArchived] = useState(false);
  const [dialog, setDialog] = useState(null);
  const [notice, setNotice] = useState('');
  useEffect(() => {
    let cancelled = false;
    setLoadError('');
    plansAPI.get(planId).then(({ data }) => { if (!cancelled) { setPlan(data); setMonth(value => value || data.start_date.slice(0, 7)); } })
      .catch(error => { if (!cancelled) setLoadError(errorMessage(error)); });
    return () => { cancelled = true; };
  }, [planId, attempt]);
  function open(type, task = null) { setError(''); setDialog({ type, task }); }
  async function mutate(action, after) {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const { data } = await action();
      setPlan(data);
      setDialog(null);
      setNotice('Đã lưu kế hoạch.');
      after?.(data);
    } catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  function saveTask(form, generate = false) {
    const payload = { ...form, revision: plan.revision };
    const previousIds = new Set(plan.tasks.map(task => task.id));
    mutate(() => dialog.task ? plansAPI.updateTask(plan.id, dialog.task.id, payload) : plansAPI.addTask(plan.id, payload), generate ? data => {
      const task = dialog.task ? data.tasks.find(item => item.id === dialog.task.id) : data.tasks.find(item => !previousIds.has(item.id));
      navigate('/', { state: { plannerBrief: { text: `Thương hiệu: ${data.brand}\nMục tiêu kế hoạch: ${data.objective}\nBài viết: ${task.title}\nKênh: ${CHANNELS[task.channel]}\n${task.brief}`, planId: data.id, taskId: task.id, title: task.title } } });
    } : null);
  }
  async function exportCSV() {
    setBusy(true); setError('');
    try { const { data } = await plansAPI.export(plan.id); downloadBlob(data, `ke-hoach-${plan.id}.csv`); }
    catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  if (!plan) return <div className="space-y-4"><Link to="/plans" className="btn btn-quiet">← Kế hoạch</Link>{loadError ? <div role="alert">{loadError}<button onClick={() => setAttempt(value => value + 1)} className="btn btn-default ml-3">Thử lại</button></div> : <p role="status">Đang mở kế hoạch…</p>}</div>;
  const active = plan.tasks.filter(task => !task.archived);
  const tasks = plan.tasks.filter(task => task.archived === showArchived && (!channel || task.channel === channel) && `${task.title} ${task.owner} ${task.brief}`.toLocaleLowerCase('vi').includes(query.toLocaleLowerCase('vi')));
  const published = active.filter(task => task.status === 'published').length;
  const overdue = active.filter(task => task.due_date && task.due_date < dateKey(new Date()) && task.status !== 'published').length;
  return <div className="space-y-6">
    <Link to="/plans" className="btn btn-quiet !px-0"><ArrowLeft size={16} />Tất cả kế hoạch</Link>
    <header className="flex flex-wrap gap-4 justify-between items-start">
      <div className="min-w-0 max-w-2xl"><p className="t-label mb-2">{plan.brand || 'Kế hoạch nội dung'} · {plan.start_date} → {plan.end_date}</p><h1 className="text-3xl md:text-4xl font-light break-words">{plan.title}</h1><p className="text-ink-2 mt-3 whitespace-pre-wrap">{plan.objective}</p></div>
      <button className="btn btn-default" disabled={busy} onClick={() => open('plan')}>Sửa kế hoạch</button>
    </header>
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">{[['Tổng bài', active.length], ['Sẵn sàng đăng', active.filter(task => task.status === 'ready').length], ['Quá hạn dự kiến', overdue], ['Đã đăng', `${published}/${active.length}`]].map(([label, value]) => <div key={label} className="sheet p-4"><p className="text-2xl font-light">{value}</p><p className="text-xs text-ink-2 mt-1">{label}</p></div>)}</div>
    <progress aria-label="Tiến độ xuất bản" value={published} max={active.length || 1} className="planner-progress w-full h-1.5" />
    <div className="flex flex-wrap gap-2 items-center">
      <button className="btn btn-primary" disabled={busy} onClick={() => open('task')}><Plus size={16} />Thêm bài</button>
      <button className="btn btn-default" disabled={busy} onClick={() => open('cadence')}><Sparkles size={16} />Dựng lịch mẫu</button>
      <button className="btn btn-default" disabled={busy} onClick={exportCSV}><Download size={16} />Xuất CSV</button>
      <button aria-label="Tải bản kế hoạch mới nhất" className="btn btn-quiet" disabled={busy} onClick={() => { setAttempt(value => value + 1); setError(''); }}><RefreshCw size={16} /></button>
      <div className="flex gap-1 ml-auto" role="group" aria-label="Chế độ xem"><button aria-pressed={view === 'board'} className={`btn ${view === 'board' ? 'btn-default' : 'btn-quiet'}`} onClick={() => setView('board')}><Columns3 size={16} />Bảng</button><button aria-pressed={view === 'calendar'} className={`btn ${view === 'calendar' ? 'btn-default' : 'btn-quiet'}`} onClick={() => setView('calendar')}><CalendarDays size={16} />Lịch</button></div>
    </div>
    <div className="flex flex-wrap items-end gap-3">
      <label className="text-xs flex-1 min-w-48">Tìm bài, brief, người phụ trách<input className={`${fieldClass} mt-1`} type="search" value={query} onChange={event => setQuery(event.target.value)} /></label>
      <label className="text-xs">Kênh<select className={`${fieldClass} mt-1`} value={channel} onChange={event => setChannel(event.target.value)}><option value="">Tất cả kênh</option>{Object.entries(CHANNELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
      <label className="flex items-center gap-2 text-sm pb-2"><input type="checkbox" checked={showArchived} onChange={event => setShowArchived(event.target.checked)} />Bài đã ẩn</label>
    </div>
    {notice && <p role="status" className="text-sm text-pass">{notice}</p>}
    {(loadError || (error && !dialog)) && <p role="alert" className="text-fail">{loadError || error}</p>}
    {!tasks.length && <section className="sheet p-6"><h2 className="font-medium">{plan.tasks.length ? 'Không có bài phù hợp bộ lọc.' : 'Kế hoạch đã sẵn sàng, hãy thêm ý tưởng đầu tiên.'}</h2><p className="text-sm text-ink-2 mt-2">Dùng “Thêm bài” cho ý tưởng riêng, hoặc “Dựng lịch mẫu” để tạo lịch nhiều tuần mà không gọi AI.</p></section>}
    {view === 'board' ? <div className="overflow-x-auto pb-4" role="region" aria-label="Bảng tiến độ nội dung" tabIndex={0}><div className="grid grid-cols-5 gap-3 min-w-[1050px]">{STAGES.map(stage => <section key={stage.id} className="rounded-2xl bg-inset border border-rule p-3 min-h-64"><header className="flex justify-between items-center mb-4 text-sm" style={{ color: stage.color }}><h2>{stage.label}</h2><span>{tasks.filter(task => task.status === stage.id).length}</span></header><div className="space-y-3">{tasks.filter(task => task.status === stage.id).map(task => <TaskCard key={task.id} task={task} onOpen={task => open('task', task)} />)}</div></section>)}</div></div>
      : <section className="space-y-4"><label className="text-sm inline-block">Tháng hiển thị<input type="month" required value={month} onChange={event => { if (event.target.value) setMonth(event.target.value); }} className={`${fieldClass} mt-1`} /></label>
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Lịch nội dung theo tháng"><div className="grid grid-cols-7 min-w-[770px] rounded-xl overflow-hidden border border-rule">{['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật'].map(day => <div key={day} className="bg-sheet p-3 text-xs text-ink-2">{day}</div>)}{monthDays(month).map(day => <div key={day} className={`min-h-32 p-2 border-t border-r border-rule ${day.startsWith(month) ? 'bg-inset' : 'bg-sheet opacity-60'}`}><p className={`text-xs mb-2 ${day === dateKey(new Date()) ? 'text-cham font-bold' : 'text-ink-2'}`}>{Number(day.slice(-2))}</p><div className="space-y-2">{tasks.filter(task => task.due_date === day).map(task => <TaskCard key={task.id} task={task} compact onOpen={task => open('task', task)} />)}</div></div>)}</div></div>
        <h2 className="text-sm font-medium">Chưa xếp lịch ({tasks.filter(task => !task.due_date).length})</h2><div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3">{tasks.filter(task => !task.due_date).map(task => <TaskCard key={task.id} task={task} onOpen={task => open('task', task)} />)}</div>
      </section>}
    <p className="text-xs text-ink-2">Lịch dùng ngày địa phương. Công cụ không tự đăng lên mạng xã hội; người phụ trách xác nhận sau khi xuất bản.</p>
    <details className="sheet p-5"><summary className="cursor-pointer text-sm">Hoạt động gần đây · phiên bản {plan.revision}</summary><ol className="mt-4 space-y-3">{plan.activity.map((event, index) => <li key={index} className="text-sm"><span className="text-ink-2 mr-3">{new Date(event.at).toLocaleString('vi-VN')}</span>{event.message}</li>)}</ol></details>
    {dialog?.type === 'plan' && <PlanForm plan={plan} onSave={form => mutate(() => plansAPI.update(plan.id, { ...form, revision: plan.revision }))} onClose={() => setDialog(null)} busy={busy} error={error} />}
    {dialog?.type === 'cadence' && <CadenceForm plan={plan} onSave={form => mutate(() => plansAPI.cadence(plan.id, { ...form, revision: plan.revision }))} onClose={() => setDialog(null)} busy={busy} error={error} />}
    {dialog?.type === 'task' && <TaskForm task={dialog.task} plan={plan} onSave={form => saveTask(form)} onGenerate={form => saveTask(form, true)} onClose={() => setDialog(null)} busy={busy} error={error} />}
  </div>;
}

export default function PlansPage() {
  const { planId } = useParams();
  return planId ? <PlanWorkspace key={planId} planId={planId} /> : <PlanIndex />;
}
