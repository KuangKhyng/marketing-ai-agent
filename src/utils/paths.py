"""
Path safety helpers — chống path traversal ở mọi chỗ nhận id/path từ user.

Nguyên tắc: KHÔNG BAO GIỜ ghép trực tiếp input của user vào Path.
Mọi id đi qua validate_id(), mọi path tương đối đi qua safe_join().
"""
import os
import re
import tempfile
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


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """
    Ghi file sao cho không bao giờ tồn tại trạng thái nửa vời.

    `path.write_text()` mở file, cắt về rỗng, rồi ghi dần. Crash hoặc hết dung
    lượng ở giữa để lại một file cụt — mà đây là knowledge base và session
    state, tức là nguồn sự thật của pipeline.

    Cách làm: ghi ra file tạm cùng thư mục (cùng filesystem nên rename mới
    atomic), fsync để dữ liệu thật sự xuống đĩa, rồi os.replace — thao tác này
    atomic ở cả POSIX lẫn Windows. Người đọc song song hoặc thấy bản cũ nguyên
    vẹn, hoặc thấy bản mới nguyên vẹn, không bao giờ thấy nửa chừng.
    """
    _atomic_write(path, text.encode(encoding))


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Bản nhị phân của atomic_write_text — dùng cho pickle."""
    _atomic_write(path, data)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    # File tạm phải nằm CÙNG thư mục: os.replace chỉ atomic trong cùng
    # filesystem, mà /tmp thường là filesystem khác với volume.
    fd, tam = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tam, path)
    except BaseException:
        # Dọn file tạm; nếu replace đã xong thì tam không còn tồn tại
        try:
            os.unlink(tam)
        except OSError:
            pass
        raise


def atomic_write_many(items: "list[tuple[Path, bytes]]") -> list[Path]:
    """
    Ghi nhiều file với MỘT điểm cam kết chung.

    Giai đoạn 1 — ghi và fsync tất cả ra file tạm. Tốn thời gian, nhưng chưa ai
    nhìn thấy gì, và hết dung lượng ở đây thì không file thật nào bị đụng.
    Giai đoạn 2 — rename lần lượt. Mỗi rename atomic và gần như tức thời.

    KHÔNG phải transaction thật: crash đúng giữa vòng rename vẫn để lại hỗn hợp
    mới/cũ. Nhưng cửa sổ rủi ro co từ "toàn bộ thời gian ghi và gọi mạng" xuống
    "vài microgiây", và không bao giờ tồn tại file cụt.

    Muốn tất-cả-hoặc-không-gì thật sự thì phải đổi sang DB có transaction —
    đó là việc của tầng persistence, không phải của filesystem.
    """
    if not items:
        return []

    tam_list: list[tuple[str, Path]] = []
    try:
        for path, data in items:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tam = tempfile.mkstemp(
                dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
            )
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            tam_list.append((tam, path))
    except BaseException:
        for tam, _ in tam_list:
            try:
                os.unlink(tam)
            except OSError:
                pass
        raise

    for tam, path in tam_list:
        os.replace(tam, path)

    return [path for _, path in tam_list]
