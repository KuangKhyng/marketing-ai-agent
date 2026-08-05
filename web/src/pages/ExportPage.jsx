import { useState } from 'react';
import { campaignAPI } from '../api/client';
import { Check, Copy, ChevronDown } from 'lucide-react';
import { useToast } from '../components/Toast';

const CHANNEL_LABEL = { facebook: 'Facebook', instagram: 'Instagram', tiktok: 'TikTok' };
const DELIVERABLE_LABEL = {
  post: 'Bài đăng',
  carousel: 'Carousel',
  reels_script: 'Kịch bản Reels',
  short_video_script: 'Kịch bản video ngắn',
  story: 'Story',
};

function formatPieceForCopy(piece) {
  const parts = [];
  if (piece.hook) parts.push(piece.hook);
  parts.push(piece.body);
  if (piece.cta_text) parts.push(`\n${piece.cta_text}`);
  if (piece.hashtags?.length > 0) parts.push(`\n${piece.hashtags.join(' ')}`);
  return parts.join('\n\n');
}

function CopyButton({ text, label = 'Sao chép', className = 'btn btn-default !py-2 !px-3 !text-[13px]' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button onClick={handleCopy} className={className}>
      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? 'Đã chép' : label}
    </button>
  );
}

export default function ExportPage({ campaignData, setPhase }) {
  const { showToast, Toast } = useToast();
  const [downloading, setDownloading] = useState(false);
  const [expanded, setExpanded] = useState(null);

  if (!campaignData) return null;
  const runId = campaignData.run_id;
  const pieces = campaignData?.content?.pieces || [];

  const handleDownload = async (format) => {
    setDownloading(true);
    try {
      const response = await campaignAPI.download(runId, format);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `campaign-${runId}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch {
      showToast('Không tải được file. Thử lại sau.');
    } finally {
      setDownloading(false);
    }
  };

  const allText = pieces
    .map(p => `=== ${CHANNEL_LABEL[p.channel] || p.channel} — ${DELIVERABLE_LABEL[p.deliverable] || p.deliverable} ===\n\n${formatPieceForCopy(p)}`)
    .join('\n\n---\n\n');

  return (
    <div className="rise">
      <header className="mb-8">
        <span className="tag tag-pass mb-3">Hoàn tất</span>
        <h1 className="t-page mb-2.5">Bàn giao</h1>
        <p className="t-lede">
          Sao chép từng bài để đăng, hoặc tải cả gói về lưu.
        </p>
        <p className="t-data mt-2">Mã chiến dịch {runId}</p>
      </header>

      {pieces.length > 0 && (
        <section className="mb-8">
          <div className="flex items-center justify-between gap-3 mb-3">
            <p className="t-label">Nội dung ({pieces.length} bài)</p>
            <CopyButton text={allText} label="Chép tất cả" />
          </div>

          <div className="sheet">
            {pieces.map((piece, i) => {
              const copyText = formatPieceForCopy(piece);
              const isOpen = expanded === i;
              return (
                <div key={i} className={i < pieces.length - 1 ? 'border-b border-rule' : ''}>
                  <div className="flex items-center justify-between gap-3 px-5 py-3.5">
                    <div className="min-w-0">
                      <p className="text-[0.9375rem] font-medium truncate">
                        {CHANNEL_LABEL[piece.channel] || piece.channel}
                        <span className="text-ink-3 font-normal">
                          {' · '}{DELIVERABLE_LABEL[piece.deliverable] || piece.deliverable}
                        </span>
                      </p>
                      <p className="t-data num mt-0.5">{piece.word_count} từ</p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <CopyButton text={copyText} />
                      <button
                        onClick={() => setExpanded(isOpen ? null : i)}
                        aria-expanded={isOpen}
                        aria-label={isOpen ? 'Thu gọn' : 'Xem trước'}
                        className="btn btn-quiet !py-2 !px-2"
                      >
                        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                      </button>
                    </div>
                  </div>

                  {isOpen && (
                    <div className="px-5 pb-5 rise">
                      <div className="inset px-4 py-3.5 max-h-72 overflow-y-auto">
                        <p className="font-copy text-[1rem] leading-[1.75] whitespace-pre-wrap">{copyText}</p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section className="mb-9">
        <p className="t-label mb-2.5">Tải về</p>
        <div className="flex flex-wrap gap-2.5">
          <button onClick={() => handleDownload('md')} disabled={downloading} className="btn btn-default">
            Markdown
          </button>
          <button onClick={() => handleDownload('json')} disabled={downloading} className="btn btn-default">
            JSON
          </button>
        </div>
      </section>

      <div className="pt-6 border-t border-rule">
        <button onClick={() => setPhase('input')} className="btn btn-primary">
          Bắt đầu chiến dịch mới
        </button>
      </div>

      <Toast />
    </div>
  );
}
