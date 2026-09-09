export const STAGES = [
  { id: 'idea', label: 'Ý tưởng', color: 'var(--ink-2)' },
  { id: 'draft', label: 'Đang viết', color: 'var(--cham)' },
  { id: 'review', label: 'Chờ duyệt', color: 'var(--warn)' },
  { id: 'ready', label: 'Sẵn sàng', color: 'var(--pass)' },
  { id: 'published', label: 'Đã đăng', color: 'var(--ink-3)' },
];
export const CHANNELS = { facebook: 'Facebook', instagram: 'Instagram', tiktok: 'TikTok' };
export const fieldClass = 'w-full rounded-xl border border-rule bg-inset px-3 py-2.5 text-sm';
export function dateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
export function monthDays(month) {
  const [year, number] = month.split('-').map(Number);
  const first = new Date(year, number - 1, 1, 12);
  const offset = (first.getDay() + 6) % 7;
  return Array.from({ length: 42 }, (_, index) => dateKey(new Date(year, number - 1, 1 - offset + index, 12)));
}
export function errorMessage(error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(item => item.msg).join(' · ');
  return detail?.message || 'Chưa kết nối được máy chủ. Vui lòng thử lại.';
}
export function taskPayload(task) {
  return Object.fromEntries(['title', 'brief', 'channel', 'owner', 'due_date', 'status', 'snapshot_id', 'piece_index', 'publication_url', 'archived'].map(key => [key, task[key]]));
}
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
