"""
Seed knowledge base vào volume.

Vấn đề: railway.toml mount volume vào /app/knowledge_base. Volume mount CHE
nội dung thư mục đó trong image, nên brand đã commit (knowledge_base/brands/*,
_global/platforms, _global/policies) hoàn toàn không thấy được ở production —
deploy mới lên là knowledge base rỗng, pipeline chạy ở chế độ generic mà không
ai biết vì sao.

Cách xử lý: nixpacks copy knowledge_base -> seed_knowledge lúc BUILD (trước khi
volume được mount, nên bản copy nằm trong image và không bị che). Lúc khởi
động, nếu volume rỗng thì copy sang.

Nguyên tắc: CHỈ copy file chưa tồn tại. Không bao giờ ghi đè nội dung người
dùng đã sửa trên volume.
"""
import logging
import shutil
from pathlib import Path

from src.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge_base"
SEED_DIR = PROJECT_ROOT / "seed_knowledge"


def _has_content(directory: Path) -> bool:
    """Thư mục có brand hoặc doc nào chưa (bỏ qua thư mục rỗng)."""
    if not directory.exists():
        return False
    return any(p.is_file() for p in directory.rglob("*"))


def seed_knowledge_base() -> int:
    """
    Copy seed vào knowledge_base cho những file còn thiếu.

    Returns:
        Số file đã copy. 0 = không cần làm gì (bình thường sau lần đầu).
    """
    if not SEED_DIR.exists():
        # Chạy local: knowledge_base là thư mục thật trong repo, không có seed
        return 0

    copied = 0
    for src in SEED_DIR.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(SEED_DIR)
        dest = KNOWLEDGE_DIR / rel
        if dest.exists():
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1

    if copied:
        logger.info("Seed knowledge base: copy %d file từ seed_knowledge/", copied)
    return copied


def warn_if_empty() -> None:
    """
    Cảnh báo to nếu knowledge base rỗng sau khi seed.

    Không phải lỗi chặn — pipeline vẫn chạy ở chế độ generic — nhưng người vận
    hành cần biết, vì content sinh ra sẽ không có giọng brand nào.
    """
    brands_dir = KNOWLEDGE_DIR / "brands"
    if not _has_content(brands_dir):
        logger.warning(
            "Knowledge base rỗng (%s). Pipeline sẽ chạy ở chế độ generic. "
            "Nếu đây là deploy mới trên volume trắng, tạo brand qua UI hoặc "
            "kiểm tra seed_knowledge/ có được copy lúc build không.",
            brands_dir,
        )
