/**
 * Đề xuất mã brand từ tên: "Phong Thuỷ Online" -> "phong_thuy_online".
 *
 * Bản rút gọn của slugify_brand_id() ở src/knowledge/brand_bootstrap.py, dùng
 * để gợi ý ngay khi gõ mà không phải hỏi server. Server vẫn là nơi kiểm cuối:
 * mã không hợp lệ sẽ bị validate_id chặn.
 */
export function slugify(name) {
  return (name || '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')   // bỏ dấu
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '_')
    .replace(/^[_-]+|[_-]+$/g, '')
    .slice(0, 64)
    .replace(/[_-]+$/, '');
}
