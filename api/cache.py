"""
CampaignCache — file-based cache for strategy and content.

Cache key = sha256(raw_input + brand_id)[:16]
TTL = 24h (based on file mtime)

Caches:
  - Phase 2 output: strategy (text)
  - Phase 3 output: master_message + campaign_content (pickle)

Only caches when there's no user feedback (feedback = unique variation, shouldn't be cached).
"""
import hashlib
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any

from src.config.settings import PROJECT_ROOT

_CACHE_DIR = PROJECT_ROOT / "outputs" / "cache"
_TTL = timedelta(hours=24)


class CampaignCache:
    def _key(self, raw_input: str, brand_id: Optional[str]) -> str:
        content = f"{raw_input.strip().lower()}|{brand_id or ''}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

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

    def get_strategy(self, raw_input: str, brand_id: Optional[str]) -> Optional[str]:
        path = _CACHE_DIR / self._key(raw_input, brand_id) / "strategy.txt"
        if self._valid(path):
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                pass
        return None

    def set_strategy(self, raw_input: str, brand_id: Optional[str], strategy: str) -> None:
        try:
            path = self._dir(self._key(raw_input, brand_id)) / "strategy.txt"
            path.write_text(strategy, encoding="utf-8")
        except Exception:
            pass

    # === Content (phase 3) ===

    def get_content(self, raw_input: str, brand_id: Optional[str]) -> Optional[dict]:
        path = _CACHE_DIR / self._key(raw_input, brand_id) / "content.pkl"
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
        master_message: Any,
        campaign_content: Any,
    ) -> None:
        try:
            path = self._dir(self._key(raw_input, brand_id)) / "content.pkl"
            with open(path, "wb") as f:
                pickle.dump(
                    {"master_message": master_message, "campaign_content": campaign_content},
                    f,
                )
        except Exception:
            pass


campaign_cache = CampaignCache()
