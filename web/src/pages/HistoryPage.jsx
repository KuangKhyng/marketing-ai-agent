import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { campaignAPI } from '../api/client';

export default function HistoryPage() {
  const [runs, setRuns] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    campaignAPI.history().then(({ data }) => {
      if (!cancelled) setRuns(data);
    }).catch(() => {
      if (!cancelled) setError(true);
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [attempt]);
  const filtered = runs.filter(run => `${run.brief_summary} ${run.run_id}`.toLocaleLowerCase('vi').includes(query.toLocaleLowerCase('vi')));
  return <div className="space-y-6">
    <header className="space-y-3">
      <h1 className="t-section">Lịch sử chiến dịch</h1>
      <p className="text-ink-2">Tìm lại các chiến dịch đã ghi nhận. Phiên làm việc có thể mở lại trong 120 phút kể từ lần lưu cuối.</p>
      <Link to="/" className="btn btn-primary">Tạo chiến dịch mới</Link>
    </header>
    <div>
      <label htmlFor="campaign-search" className="block mb-2">Tìm chiến dịch</label>
      <input id="campaign-search" type="search" value={query} onChange={event => setQuery(event.target.value)}
        placeholder="Nhập nội dung brief hoặc mã chiến dịch" className="w-full rounded-xl border border-rule bg-transparent p-3" />
    </div>
    {loading ? <p role="status">Đang tải lịch sử…</p> : error ? <div role="alert" className="sheet p-6 space-y-3">
      <p>Chưa tải được lịch sử. Vui lòng thử lại.</p>
      <button className="btn btn-default" onClick={() => setAttempt(value => value + 1)}>Thử lại</button>
    </div> : filtered.length === 0 ? <p className="sheet p-6">{runs.length ? 'Không tìm thấy chiến dịch phù hợp.' : 'Chưa có chiến dịch nào được ghi nhận.'}</p> :
      <ul className="space-y-3">{filtered.map(run => <li key={run.run_id} className="sheet p-5 space-y-3">
        <h2 className="font-medium break-words">{run.brief_summary || 'Chiến dịch chưa có tóm tắt'}</h2>
        <p className="text-sm text-ink-2 break-all">{run.run_id}</p>
        <div className="flex flex-wrap justify-between items-center gap-3">
          <span className="text-sm text-ink-2">{Number.isNaN(Date.parse(run.timestamp)) ? 'Chưa có thời gian' : new Date(run.timestamp).toLocaleString('vi-VN')}</span>
          <Link className="btn btn-default" to={`/?run=${encodeURIComponent(run.run_id)}`}>Mở chiến dịch</Link>
        </div>
      </li>)}</ul>}
  </div>;
}
