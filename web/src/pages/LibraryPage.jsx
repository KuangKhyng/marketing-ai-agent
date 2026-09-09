import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { libraryAPI } from '../api/client';

export default function LibraryPage() {
  const { snapshotId } = useParams();
  const [result, setResult] = useState(null);
  const data = result && result.id === snapshotId ? result.data : null;
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState('');
  useEffect(() => {
    let cancelled = false;
    setResult(null);
    setError('');
    setDownloadError('');
    (snapshotId ? libraryAPI.get(snapshotId) : libraryAPI.list()).then(response => {
      if (!cancelled) setResult({ id: snapshotId, data: response.data });
    }).catch(failure => {
      if (!cancelled) setError(failure.response?.status === 404 ? 'Bản lưu này không tồn tại.' : 'Chưa tải được thư viện. Vui lòng thử lại.');
    });
    return () => { cancelled = true; };
  }, [snapshotId, attempt]);
  async function download() {
    setDownloading(true);
    setDownloadError('');
    try {
      const response = await libraryAPI.download(snapshotId);
      const url = URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `campaign-${snapshotId}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch { setDownloadError('Chưa tải được file. Vui lòng thử lại.'); }
    finally { setDownloading(false); }
  }
  const review = data?.campaign?.review_result;
  const filtered = Array.isArray(data) ? data.filter(item => `${item.title} ${item.run_id}`.toLocaleLowerCase('vi').includes(query.toLocaleLowerCase('vi'))) : [];
  return <div className="space-y-6">
    <header className="space-y-3">
      {snapshotId && <Link to="/library" className="btn btn-quiet">← Thư viện</Link>}
      <h1 className="t-page break-words">{snapshotId ? data?.title || 'Bản lưu chiến dịch' : 'Thư viện nội dung'}</h1>
      <p className="t-lede">Các phiên bản được lưu riêng, không hết hạn theo phiên làm việc. Lưu vào thư viện không đồng nghĩa với đã duyệt đăng.</p>
    </header>
    {error ? <div role="alert" className="sheet p-6 space-y-3"><p>{error}</p><button className="btn btn-default" onClick={() => setAttempt(value => value + 1)}>Thử lại</button></div>
      : !data ? <p role="status">Đang tải thư viện…</p>
      : snapshotId ? <>
        <div className="flex flex-wrap gap-3 items-center">
          <span className="tag">{review?.review_unavailable ? 'Kiểm duyệt chưa khả dụng' : review?.overall_passed ? 'Đạt kiểm duyệt AI' : review ? 'Cần chỉnh sửa' : 'Chưa kiểm duyệt'}</span>
          <span className="text-sm text-ink-2">Lưu lúc {new Date(data.saved_at).toLocaleString('vi-VN')}</span>
          <button className="btn btn-default" disabled={downloading} onClick={download}>{downloading ? 'Đang tải…' : 'Tải bản lưu JSON'}</button>
        </div>
        {downloadError && <p role="alert">{downloadError}</p>}
        {data.campaign.warnings?.length > 0 && <div role="note" className="sheet p-5"><p className="font-medium mb-2">Lưu ý của chiến dịch</p><ul className="list-disc pl-5">{data.campaign.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul></div>}
        {data.campaign.content?.pieces?.map((piece, i) => <article key={i} className="sheet p-6 space-y-3">
          <h2 className="font-medium">{piece.channel} · {piece.deliverable}</h2>
          {piece.hook && <p className="font-medium whitespace-pre-wrap">{piece.hook}</p>}
          <p className="whitespace-pre-wrap leading-relaxed break-words">{piece.body}</p>
          {piece.cta_text && <p className="whitespace-pre-wrap">{piece.cta_text}</p>}
          <p className="text-sm text-ink-2 break-words">{piece.hashtags?.join(' ')}</p>
        </article>)}
        <details className="sheet p-5"><summary className="cursor-pointer">Chiến lược và kết quả kiểm duyệt gốc</summary><pre className="mt-4 text-sm whitespace-pre-wrap break-words">{JSON.stringify({ strategy: data.campaign.strategy, review_result: review }, null, 2)}</pre></details>
      </> : <>
        <div><label htmlFor="library-search" className="block mb-2">Tìm theo tên hoặc mã chiến dịch</label><input id="library-search" type="search" value={query} onChange={event => setQuery(event.target.value)} className="w-full border border-rule rounded-xl p-3 bg-transparent" /></div>
        {data.length > 0 && filtered.length === 0 && <p role="status" className="sheet p-5">Không có bản lưu phù hợp. Thử tên hoặc mã khác.</p>}
        {data.length === 0 ? <div className="sheet p-7 space-y-3"><h2 className="font-medium">Giữ lại những phương án đáng dùng</h2><p>Tạo nội dung, đặt tên bản lưu rồi bấm “Lưu phiên bản”. Bạn có thể lưu nhiều phương án để so sánh về sau.</p><Link className="btn btn-primary" to="/">Tạo chiến dịch</Link></div> : <ul className="space-y-3">{filtered.map(item => <li key={item.id}><Link to={`/library/${item.id}`} className="sheet block p-5 space-y-2 hover:underline"><h2 className="font-medium break-words">{item.title}</h2><p className="text-sm text-ink-2">{item.piece_count} bài · {new Date(item.saved_at).toLocaleString('vi-VN')}</p></Link></li>)}</ul>}
      </>}
  </div>;
}
