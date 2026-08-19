"""
CampaignCache — file-based cache for strategy and content.

Cache key phải chứa MỌI thứ ảnh hưởng tới output, nếu không cache sẽ trả về
kết quả của một brief/strategy khác:

    strategy key = raw_input + brand_id + digest(brief)
    content key  = raw_input + brand_id + digest(brief) + strategy

Hai điểm quan trọng:

1. `strategy` nằm trong content key. Nhờ vậy khi user yêu cầu sửa chiến lược,
   key đổi → cache miss → content được sinh lại từ chiến lược MỚI. Trước đây
   key chỉ có raw_input nên bản sửa của user bị bỏ qua âm thầm.

2. `digest(brief)` nằm trong cả hai key. Nhờ vậy chiến lược sinh từ brief đã
   chỉnh không còn ghi đè lên key của brief gốc.

TTL = 24h (theo file mtime).
Run đã đi qua vòng sửa của user thì không đọc/ghi cache — xem `is_cacheable`.
"""
import hashlib
import logging
import pickle
from functools import lru_cache
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any

from src.config.settings import PROJECT_ROOT
from src.utils.paths import atomic_write_bytes, atomic_write_text

logger = logging.getLogger(__name__)

_CACHE_DIR = PROJECT_ROOT / "outputs" / "cache"
_TTL = timedelta(hours=24)

# Tăng số này khi schema của object được pickle thay đổi. Key đổi theo nên file
# cũ bị bỏ qua, thay vì unpickle ra object thiếu field.
_SCHEMA_VERSION = "2"


def _digest(*parts: str) -> str:
    """Hash các thành phần của key. Có separator để ('a','bc') != ('ab','c')."""
    h = hashlib.sha256()
    h.update(_SCHEMA_VERSION.encode("utf-8"))
    for p in parts:
        h.update(b"\x1f")
        h.update((p or "").strip().lower().encode("utf-8"))
    return h.hexdigest()[:16]


@lru_cache(maxsize=1)
def _system_digest(dau_van: float) -> str:
    """
    Chữ ký của prompt + cấu hình model.

    Sửa prompt hoặc đổi model thì kết quả cũ không còn so sánh được nữa, phải
    sinh lại. Tham số `dau_van` là mtime lớn nhất trong các file đó — đổi file
    là đổi khoá, không cần restart server.
    """
    h = hashlib.sha256()
    for path in sorted(_SYSTEM_FILES):
        if path.exists():
            h.update(path.read_bytes())
    return h.hexdigest()[:12]


def _system_files() -> list[Path]:
    files = list((PROJECT_ROOT / "src" / "prompts" / "v1").glob("*.md"))
    files.append(PROJECT_ROOT / "src" / "config" / "models.yaml")
    return files


_SYSTEM_FILES = _system_files()


def system_version() -> str:
    """Phiên bản prompt+model hiện tại, dùng làm một phần khoá cache."""
    mtimes = [p.stat().st_mtime for p in _SYSTEM_FILES if p.exists()]
    return _system_digest(max(mtimes) if mtimes else 0.0)


def knowledge_digest(context_pack: Any) -> str:
    """
    Chữ ký của knowledge đã thật sự được nạp cho lần chạy này.

    Lấy từ context_pack chứ không phải quét cả knowledge_base: cái vào prompt
    mới là cái ảnh hưởng kết quả. Sửa một brand khác thì không cần bỏ cache của
    brand này.
    """
    if not isinstance(context_pack, dict):
        return ""

    h = hashlib.sha256()
    for khoa in sorted(context_pack):
        if khoa in ("loaded_docs", "mode", "brand_id"):
            continue  # metadata, không phải nội dung
        h.update(khoa.encode("utf-8"))
        h.update(b"\x1f")
        h.update(repr(context_pack[khoa]).encode("utf-8", "replace"))
    return h.hexdigest()[:16]


def _brief_digest(brief: Any) -> str:
    """Chữ ký của brief. None = chưa parse xong → chuỗi rỗng."""
    if brief is None:
        return ""
    dump = getattr(brief, "model_dump_json", None)
    return dump() if callable(dump) else str(brief)


def is_cacheable(state: dict) -> bool:
    """
    Run đã có feedback của user thì không dùng cache nữa.

    feedback nghĩa là user muốn một bản KHÁC — trả lại bản cũ từ cache là sai,
    kể cả khi feedback lặp lại y nguyên.
    """
    return not state.get("strategy_feedback") and state.get("review_result") is None


class CampaignCache:
    def _valid(self, path: Path) -> bool:
        if not path.exists():
            return False
        age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
        return age < _TTL

    def _dir(self, key: str) -> Path:
        d = _CACHE_DIR / key
        d.mkdir(parents=True, exist_ok=True)
        return d

    # === Strategy (phase 2) ===

    def strategy_key(
        self,
        raw_input: str,
        brand_id: Optional[str],
        brief: Any,
        context_pack: Any = None,
    ) -> str:
        return _digest(
            "strategy",
            raw_input,
            brand_id or "",
            _brief_digest(brief),
            knowledge_digest(context_pack),
            system_version(),
        )

    def get_strategy(
        self,
        raw_input: str,
        brand_id: Optional[str],
        brief: Any = None,
        context_pack: Any = None,
    ) -> Optional[str]:
        key = self.strategy_key(raw_input, brand_id, brief, context_pack)
        path = _CACHE_DIR / key / "strategy.txt"
        if self._valid(path):
            try:
                return path.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning("Không đọc được strategy cache %s: %s", path, e)
        return None

    def set_strategy(
        self,
        raw_input: str,
        brand_id: Optional[str],
        brief: Any,
        strategy: str,
        context_pack: Any = None,
    ) -> None:
        try:
            key = self.strategy_key(raw_input, brand_id, brief, context_pack)
            atomic_write_text(self._dir(key) / "strategy.txt", strategy)
        except OSError as e:
            logger.warning("Không ghi được strategy cache: %s", e)

    # === Content (phase 3) ===

    def content_key(
        self,
        raw_input: str,
        brand_id: Optional[str],
        brief: Any,
        strategy: Optional[str],
        context_pack: Any = None,
    ) -> str:
        return _digest(
            "content",
            raw_input,
            brand_id or "",
            _brief_digest(brief),
            strategy or "",
            knowledge_digest(context_pack),
            system_version(),
        )

    def get_content(
        self,
        raw_input: str,
        brand_id: Optional[str],
        brief: Any = None,
        strategy: Optional[str] = None,
        context_pack: Any = None,
    ) -> Optional[dict]:
        key = self.content_key(raw_input, brand_id, brief, strategy, context_pack)
        path = _CACHE_DIR / key / "content.pkl"
        if self._valid(path):
            try:
                with open(path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                # Thường là schema đã đổi — xoá để lần sau khỏi thử lại
                logger.info("Bỏ content cache không đọc được %s: %s", path, e)
                path.unlink(missing_ok=True)
        return None

    def set_content(
        self,
        raw_input: str,
        brand_id: Optional[str],
        brief: Any,
        strategy: Optional[str],
        master_message: Any,
        campaign_content: Any,
        context_pack: Any = None,
    ) -> None:
        try:
            key = self.content_key(raw_input, brand_id, brief, strategy, context_pack)
            atomic_write_bytes(
                self._dir(key) / "content.pkl",
                pickle.dumps(
                    {"master_message": master_message, "campaign_content": campaign_content}
                ),
            )
        except Exception as e:
            logger.warning("Không ghi được content cache: %s", e)


campaign_cache = CampaignCache()
