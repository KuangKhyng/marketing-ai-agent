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
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any

from src.config.settings import PROJECT_ROOT

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

    def strategy_key(self, raw_input: str, brand_id: Optional[str], brief: Any) -> str:
        return _digest("strategy", raw_input, brand_id or "", _brief_digest(brief))

    def get_strategy(
        self, raw_input: str, brand_id: Optional[str], brief: Any = None
    ) -> Optional[str]:
        path = _CACHE_DIR / self.strategy_key(raw_input, brand_id, brief) / "strategy.txt"
        if self._valid(path):
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                pass
        return None

    def set_strategy(
        self, raw_input: str, brand_id: Optional[str], brief: Any, strategy: str
    ) -> None:
        try:
            key = self.strategy_key(raw_input, brand_id, brief)
            (self._dir(key) / "strategy.txt").write_text(strategy, encoding="utf-8")
        except Exception:
            pass

    # === Content (phase 3) ===

    def content_key(
        self, raw_input: str, brand_id: Optional[str], brief: Any, strategy: Optional[str]
    ) -> str:
        return _digest(
            "content", raw_input, brand_id or "", _brief_digest(brief), strategy or ""
        )

    def get_content(
        self,
        raw_input: str,
        brand_id: Optional[str],
        brief: Any = None,
        strategy: Optional[str] = None,
    ) -> Optional[dict]:
        path = _CACHE_DIR / self.content_key(raw_input, brand_id, brief, strategy) / "content.pkl"
        if self._valid(path):
            try:
                with open(path, "rb") as f:
                    return pickle.load(f)
            except Exception:
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
    ) -> None:
        try:
            key = self.content_key(raw_input, brand_id, brief, strategy)
            with open(self._dir(key) / "content.pkl", "wb") as f:
                pickle.dump(
                    {"master_message": master_message, "campaign_content": campaign_content},
                    f,
                )
        except Exception:
            pass


campaign_cache = CampaignCache()
