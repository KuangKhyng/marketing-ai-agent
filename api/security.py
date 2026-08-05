"""
API key authentication.

Client gửi key qua header `X-API-Key`. Server đọc danh sách key hợp lệ từ
biến môi trường `APP_API_KEY` (nhiều key ngăn cách bằng dấu phẩy — tiện khi
cần revoke từng người mà không đổi key của cả nhóm).

Hành vi khi APP_API_KEY chưa được set:
  - ENV=dev/development/local  → tắt auth (chạy local cho tiện)
  - còn lại (production)       → CHẶN mọi request với 503

Fail-closed ở production là cố ý: thà app không chạy còn hơn mở toang API
đốt token Anthropic. Nhớ set APP_API_KEY trên Railway trước khi deploy.
"""
import hmac
import os

from fastapi import Header, HTTPException


def is_dev() -> bool:
    return os.getenv("ENV", "production").lower() in ("dev", "development", "local")


def _configured_keys() -> list[str]:
    """Đọc key tại thời điểm gọi (không cache) để đổi env là có hiệu lực ngay."""
    raw = os.getenv("APP_API_KEY", "")
    return [k.strip() for k in raw.split(",") if k.strip()]


def auth_enabled() -> bool:
    """Auth có đang bật không — dùng cho endpoint /auth/status."""
    return bool(_configured_keys())


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """
    FastAPI dependency — gắn vào router để bảo vệ toàn bộ endpoint bên trong.

    Raises:
        HTTPException 503: production nhưng chưa cấu hình APP_API_KEY
        HTTPException 401: thiếu key hoặc key sai
    """
    keys = _configured_keys()

    if not keys:
        if is_dev():
            return  # local dev — bỏ qua auth
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Server chưa được cấu hình. Vui lòng liên hệ quản trị viên.",
                "hint": "Thiếu biến môi trường APP_API_KEY",
            },
        )

    # compare_digest để tránh timing attack khi so sánh key
    if not x_api_key or not any(hmac.compare_digest(x_api_key, k) for k in keys):
        raise HTTPException(
            status_code=401,
            detail={"message": "Access key không hợp lệ hoặc đã hết hạn."},
        )
