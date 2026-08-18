/**
 * Hiện chi phí một lượt đọc.
 *
 * Số tiền thường rất nhỏ ($0.02–0.1) nên làm tròn 2 chữ số sẽ ra "$0.00" —
 * mà "$0.00" thì người đọc hiểu là miễn phí, sai hoàn toàn. Dưới 1 cent thì
 * hiện "<$0.01".
 */
export function formatCost(usd) {
  if (usd == null) return '—';
  if (usd === 0) return 'miễn phí';
  if (usd < 0.01) return '<$0.01';
  return `$${usd.toFixed(2)}`;
}
