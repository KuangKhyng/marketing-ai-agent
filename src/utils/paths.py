"""
Path safety helpers — chống path traversal ở mọi chỗ nhận id/path từ user.

Nguyên tắc: KHÔNG BAO GIỜ ghép trực tiếp input của user vào Path.
Mọi id đi qua validate_id(), mọi path tương đối đi qua safe_join().
"""
import re
from pathlib import Path

# id an toàn: chữ, số, gạch ngang, gạch dưới — đủ cho brand_id, run_id, template_id
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class InvalidPathError(ValueError):
    """Id hoặc path từ user không an toàn. Route layer map thành HTTP 400."""


def validate_id(value: str, label: str = "id") -> str:
    """
    Kiểm tra một id dùng làm tên thư mục/file.

    Raises:
        InvalidPathError: nếu id rỗng, sai kiểu, hoặc chứa ký tự ngoài [A-Za-z0-9_-].
    """
    if not isinstance(value, str) or not _ID_RE.match(value):
        raise InvalidPathError(
            f"{label} không hợp lệ: chỉ cho phép chữ, số, '-' và '_' (tối đa 64 ký tự)"
        )
    return value


def is_valid_id(value: str) -> bool:
    """Bản không raise của validate_id — dùng khi duyệt filesystem."""
    return isinstance(value, str) and bool(_ID_RE.match(value))


def safe_join(base: Path, *parts: str) -> Path:
    """
    Ghép path tương đối vào base và đảm bảo kết quả vẫn nằm trong base.

    Chặn được '..', path tuyệt đối, và symlink trỏ ra ngoài (vì resolve()
    đi theo symlink trước khi so sánh).

    Raises:
        InvalidPathError: nếu path thoát ra ngoài base.
    """
    for part in parts:
        if not isinstance(part, str) or "\x00" in part:
            raise InvalidPathError("Đường dẫn chứa ký tự không hợp lệ")

    base_resolved = base.resolve()
    try:
        # strict=False: file chưa tồn tại vẫn resolve được (cần cho thao tác tạo mới)
        resolved = base_resolved.joinpath(*parts).resolve(strict=False)
    except (OSError, ValueError) as e:
        raise InvalidPathError("Đường dẫn không hợp lệ") from e

    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise InvalidPathError("Đường dẫn nằm ngoài thư mục cho phép")

    return resolved
