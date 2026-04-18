"""
Context Retriever — brand-aware context assembly.

Source-of-truth hierarchy (priority cao → thấp):
1. User input (brief.additional_context)
2. Brand-specific policies → global policies
3. Brand identity + tone
4. Product facts
5. Audience personas
6. Platform rules (global)
7. Voice profile

Supports two modes:
- branded: Load knowledge from brands/{brand_id}/
- generic: No brand context, generic voice profile
"""
import json
import re
from pathlib import Path
from functools import lru_cache
from hashlib import md5

from src.models.brief import CampaignBrief
from src.config.settings import PROJECT_ROOT

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge_base"
BRANDS_DIR = KNOWLEDGE_DIR / "brands"
GLOBAL_DIR = KNOWLEDGE_DIR / "_global"

@lru_cache(maxsize=100)
def _read_file_cached(filepath: str, mtime: float) -> str:
    """Cache file content, invalidate khi file thay đổi."""
    return Path(filepath).read_text(encoding="utf-8")

def _read_file(filepath: Path) -> str:
    """Read file with caching."""
    if filepath.exists():
        mtime = filepath.stat().st_mtime
        return _read_file_cached(str(filepath), mtime)
    return ""


def build_context_pack(brief: CampaignBrief, brand_id: str = None) -> dict:
    """
    Assemble the full context pack for a campaign brief.

    Args:
        brief: Parsed CampaignBrief from brief_parser node.
        brand_id: Brand ID to load knowledge from. None = generic mode.

    Returns:
        context_pack dict.
    """
    context = {
        "brand": "",
        "product": "",
        "audience": "",
        "platform_rules": {},
        "policies": "",
        "voice_profile": {},
        "additional_context": brief.additional_context or "",
        "brand_id": brand_id or "",
        "mode": "branded" if brand_id else "generic",
        "brand_name": "",
        "loaded_docs": [],
    }

    # === ALWAYS LOAD: Global platform rules ===
    channels = [c.value for c in brief.channels]
    platforms_dir = GLOBAL_DIR / "platforms"
    if platforms_dir.exists():
        for channel in channels:
            filepath = platforms_dir / f"{channel}.md"
            if filepath.exists():
                context["platform_rules"][channel] = _read_file(filepath)
                context["loaded_docs"].append(f"platform:{channel}")

    # === ALWAYS LOAD: Global content policies ===
    policies_parts = []
    policies_dir = GLOBAL_DIR / "policies"
    if policies_dir.exists():
        for f in policies_dir.glob("*.md"):
            policies_parts.append(_read_file(f))
            context["loaded_docs"].append(f"global_policy:{f.stem}")

    # === BRAND-SPECIFIC MODE ===
    if brand_id:
        brand_dir = BRANDS_DIR / brand_id
        if not brand_dir.exists():
            # Brand not found — fall back to generic
            context["mode"] = "generic"
            context["voice_profile"] = _get_generic_voice_profile()
            context["policies"] = "\n\n---\n\n".join(policies_parts)
            return context

        # Brand identity + tone + visual
        brand_parts = []
        for filename in ["identity.md", "tone_of_voice.md", "visual_guidelines.md"]:
            filepath = brand_dir / filename
            if filepath.exists():
                brand_parts.append(_read_file(filepath))
                context["loaded_docs"].append(f"brand:{filename.replace('.md', '')}")
        context["brand"] = "\n\n---\n\n".join(brand_parts)

        # Products — SMART load: only matching files
        product_content, p_docs = _smart_load_dir(
            brand_dir / "products",
            query=f"{brief.offer.product_or_service} {brief.offer.key_message}",
            max_files=2,
        )
        context["product"] = product_content
        context["loaded_docs"].extend([f"product:{d}" for d in p_docs])

        # Audience — SMART load: only matching files
        audience_content, a_docs = _smart_load_dir(
            brand_dir / "audience",
            query=brief.audience.persona_description,
            max_files=1,
        )
        context["audience"] = audience_content
        context["loaded_docs"].extend([f"audience:{d}" for d in a_docs])

        # Voice profile
        voice_path = brand_dir / "voice_profile.json"
        if voice_path.exists():
            context["voice_profile"] = json.loads(_read_file(voice_path))
            context["loaded_docs"].append("voice_profile")
        else:
            context["voice_profile"] = _get_generic_voice_profile()

        # Brand-specific policies (merge with global)
        brand_policies_dir = brand_dir / "policies"
        if brand_policies_dir.exists():
            for f in brand_policies_dir.glob("*.md"):
                policies_parts.append(_read_file(f))
                context["loaded_docs"].append(f"brand_policy:{f.stem}")

        # Brand metadata (forbidden claims, mandatory terms)
        meta_path = brand_dir / "brand.json"
        if meta_path.exists():
            meta = json.loads(_read_file(meta_path))
            context["brand_meta"] = meta
            context["brand_name"] = meta.get("name", "")

    else:
        # === GENERIC MODE ===
        context["voice_profile"] = _get_generic_voice_profile()
        context["audience"] = f"Target audience: {brief.audience.persona_description}"

    context["policies"] = "\n\n---\n\n".join(policies_parts)
    return context


def _get_generic_voice_profile() -> dict:
    """Default voice profile for generic (no-brand) mode."""
    return {
        "profile_id": "generic",
        "tone": {"primary": "friendly-professional", "formality": 0.5},
        "writing_style": {"avg_sentence_length": 15, "perspective": "second_person"},
        "vocabulary": {"preferred": [], "avoided": [], "emoji_style": "moderate"},
        "anti_ai_rules": [
            "Never start with 'Bạn đã bao giờ'",
            "Avoid 'Trong thế giới hiện đại'",
            "Avoid 'Không chỉ vậy', 'Hơn thế nữa'",
        ],
    }

def _smart_load_dir(directory: Path, query: str, max_files: int = 2) -> tuple[str, list[str]]:
    """
    Smart load files from a directory — only load files matching query keywords.

    Returns:
        tuple(content_string, list_of_filenames_loaded)
    """
    if not directory.exists():
        return "", []

    files = [f for f in directory.glob("*.md") if not f.stem.startswith("_")]
    if not files:
        # Try loading template as fallback
        template = directory / "_template.md"
        if template.exists():
            content = _read_file(template)
            # Skip empty templates with placeholder text
            if content.strip() and "(Thêm" not in content[:50]:
                return content, ["_template"]
        return "", []

    if len(files) == 1:
        # Only 1 file — just load it
        return _read_file(files[0]), [files[0].stem]

    # Multiple files — score by keyword match
    keywords = _extract_keywords(query)
    if not keywords:
        # No useful keywords — load first file as fallback
        return _read_file(files[0]), [files[0].stem]

    scored = []
    for filepath in files:
        content = _read_file(filepath).lower()
        filename = filepath.stem.replace("_", " ").lower()

        score = 0
        for kw in keywords:
            if kw in filename:
                score += 3  # Filename match = high weight
            if kw in content[:500]:  # Only check beginning (title, description)
                score += 1

        scored.append((filepath, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    # Take top matches with score > 0, up to max_files
    matches = [f for f, s in scored if s > 0][:max_files]

    if not matches:
        # No keyword match at all — load first file as fallback
        matches = [files[0]]

    parts = [_read_file(f) for f in matches]
    loaded_names = [f.stem for f in matches]
    return "\n\n---\n\n".join(parts), loaded_names


def _extract_keywords(text: str) -> list[str]:
    """
    Extract meaningful keywords from Vietnamese text.
    Removes stop words, keeps nouns and key terms.
    """
    # Vietnamese + English stop words (common, non-meaningful)
    stop_words = {
        "là", "và", "của", "cho", "với", "trong", "để", "có", "không",
        "được", "từ", "này", "đó", "các", "một", "những", "tôi", "bạn",
        "mình", "như", "thì", "khi", "nếu", "hay", "hoặc", "cũng",
        "đã", "sẽ", "đang", "rất", "lại", "ra", "vào", "lên", "về",
        "qua", "theo", "tại", "bởi", "mà", "thế", "nào", "gì",
        "campaign", "tạo", "viết", "content", "target", "marketing",
        "awareness", "engagement", "conversion", "lead", "post",
        "dịch", "vụ", "sản", "phẩm", "dùng", "làm", "sao", "thế",
        "online", "offline", "channels", "channel",
    }

    # Tokenize: extract words (including Vietnamese diacritics)
    words = re.findall(
        r'[a-zA-Zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]+',
        text.lower()
    )

    seen = set()
    result = []
    for w in words:
        if w not in stop_words and len(w) > 1 and w not in seen:
            seen.add(w)
            result.append(w)

    return result
