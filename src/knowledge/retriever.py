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
import logging
import re
from pathlib import Path
from functools import lru_cache
from hashlib import md5

from src.knowledge.untrusted import wrap as wrap_untrusted
from src.models.brief import CampaignBrief
from src.config.settings import PROJECT_ROOT
from src.utils.paths import InvalidPathError, safe_join, validate_id

logger = logging.getLogger(__name__)

# Nhắc thẳng vào context khi không tra được tài liệu. Cố ý viết như một chỉ
# dẫn chứ không phải một ghi chú: nó nằm trong phần dữ liệu mà node đưa cho LLM.
KHONG_CO_BANG_CHUNG_SAN_PHAM = (
    "KHÔNG tìm được tài liệu sản phẩm nào khớp với yêu cầu này trong kho brand.\n"
    "TUYỆT ĐỐI không bịa đặc điểm, thành phần, giá, thông số hay cam kết. "
    "Chỉ viết ở mức chung dựa trên brief, và tránh mọi khẳng định cụ thể về sản phẩm."
)

KHONG_CO_BANG_CHUNG_KHACH = (
    "KHÔNG tìm được chân dung khách hàng nào khớp trong kho brand.\n"
    "Chỉ dựa vào mô tả đối tượng trong brief, không bịa thêm hành vi, thu nhập "
    "hay trăn trở mà không có căn cứ."
)

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
        # Có tra được tài liệu thật không. False = LLM phải kiêng nói cụ thể.
        "product_evidence": False,
        "audience_evidence": False,
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
            policies_parts.append(
                wrap_untrusted(f"policy/global/{f.stem}", "policy", _read_file(f))
            )
            context["loaded_docs"].append(f"global_policy:{f.stem}")

    # === BRAND-SPECIFIC MODE ===
    if brand_id:
        try:
            validate_id(brand_id, "brand_id")
            brand_dir = safe_join(BRANDS_DIR, brand_id)
        except InvalidPathError:
            brand_dir = None

        if brand_dir is None or not brand_dir.exists():
            # Brand không tồn tại (vd: bị xoá giữa run) — rơi về generic.
            # Content sẽ mất giọng brand nên phải log, đừng lặng lẽ.
            logger.warning(
                "Brand '%s' không tìm thấy — sinh content ở chế độ generic", brand_id
            )
            context["mode"] = "generic"
            context["voice_profile"] = _get_generic_voice_profile()
            context["policies"] = "\n\n".join(policies_parts)
            return context

        # Brand identity + tone + visual
        brand_parts, brand_names = [], []
        for filename in [
            "identity.md",
            "tone_of_voice.md",
            "content_framework.md",   # khung bài, sinh từ bootstrap
            "visual_guidelines.md",
        ]:
            filepath = brand_dir / filename
            if filepath.exists():
                brand_parts.append(_read_file(filepath))
                brand_names.append(filename)
                context["loaded_docs"].append(f"brand:{filename.replace('.md', '')}")
        context["brand"] = "\n\n".join(
            wrap_untrusted(f"brand/{ten}", "brand", noi_dung)
            for ten, noi_dung in zip(brand_names, brand_parts)
        )

        # Products — SMART load: only matching files
        product_content, p_docs = _smart_load_dir(
            brand_dir / "products",
            query=f"{brief.offer.product_or_service} {brief.offer.key_message}",
            max_files=2,
        )
        context["product"] = (
            "\n\n".join(
                wrap_untrusted(f"product/{ten}", "product", product_content)
                for ten in [", ".join(p_docs) or "unknown"]
            )
            if product_content
            else KHONG_CO_BANG_CHUNG_SAN_PHAM
        )
        context["product_evidence"] = bool(p_docs)
        context["loaded_docs"].extend([f"product:{d}" for d in p_docs])

        # Audience — SMART load: only matching files
        audience_content, a_docs = _smart_load_dir(
            brand_dir / "audience",
            query=brief.audience.persona_description,
            max_files=1,
        )
        context["audience"] = (
            wrap_untrusted(f"audience/{', '.join(a_docs)}", "audience", audience_content)
            if audience_content
            else KHONG_CO_BANG_CHUNG_KHACH
        )
        context["audience_evidence"] = bool(a_docs)
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
                policies_parts.append(
                    wrap_untrusted(f"policy/{brand_id}/{f.stem}", "policy", _read_file(f))
                )
                context["loaded_docs"].append(f"brand_policy:{f.stem}")

        # Brand metadata (forbidden claims, mandatory terms)
        # Chỉ lấy tên brand. forbidden_claims / mandatory_terms KHÔNG đi qua
        # đây — brief_parser._override_brand_from_state nạp chúng vào
        # brief.brand từ brand.json, và reviewer đọc từ brief. Trước đây cả
        # meta được nhét vào context["brand_meta"] mà không ai đọc.
        meta_path = brand_dir / "brand.json"
        if meta_path.exists():
            meta = json.loads(_read_file(meta_path))
            context["brand_name"] = meta.get("name", "")

    else:
        # === GENERIC MODE ===
        context["voice_profile"] = _get_generic_voice_profile()
        context["audience"] = f"Target audience: {brief.audience.persona_description}"
        # Không chọn brand thì không có kho sản phẩm nào để dựa vào
        context["product"] = KHONG_CO_BANG_CHUNG_SAN_PHAM
        context["product_evidence"] = False
        context["audience_evidence"] = False

    context["policies"] = "\n\n".join(policies_parts)
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
    Nạp tài liệu khớp với yêu cầu.

    KHÔNG có fallback lấy bừa. Không khớp thì trả rỗng, và người gọi sẽ ghi
    lời nhắc "không có bằng chứng" vào context. Đưa nhầm tài liệu vào còn tệ
    hơn không đưa gì: LLM sẽ coi nó là sự thật, và reviewer chấm factuality
    dựa trên chính tài liệu sai đó nên không bắt được.

    Returns:
        (nội dung, tên file đã nạp). Rỗng nghĩa là không có bằng chứng.
    """
    if not directory.exists():
        return "", []

    files = [f for f in directory.glob("*.md") if not f.stem.startswith("_")]
    if not files:
        return "", []

    keywords = _extract_keywords(query)
    if not keywords:
        logger.info(
            "%s: yêu cầu không có từ khoá nào dùng được — không nạp tài liệu nào",
            directory.name,
        )
        return "", []

    scored = []
    for filepath in files:
        content = _read_file(filepath).lower()
        filename = filepath.stem.replace("_", " ").lower()

        score = 0
        for kw in keywords:
            if kw in filename:
                score += 3          # khớp tên file = tín hiệu mạnh
            if kw in content:       # quét TOÀN VĂN, không chỉ 500 ký tự đầu
                score += 1
        scored.append((filepath, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    relevant = [f for f, sc in scored if sc > 0]

    if not relevant:
        logger.warning(
            "%s: không tài liệu nào khớp '%s' — không nạp gì, LLM sẽ được dặn không bịa",
            directory.name, query[:60],
        )
        return "", []

    matches = relevant[:max_files]
    if len(relevant) > max_files:
        # Retrieval ở đây là keyword scoring, không phải vector search. File bị
        # cắt bỏ vẫn có thể liên quan — log để biết context đang thiếu gì.
        logger.info(
            "%s: có %d file khớp nhưng chỉ nạp %d — bỏ %s",
            directory.name, len(relevant), max_files,
            ", ".join(f.name for f in relevant[max_files:]),
        )

    return "\n\n---\n\n".join(_read_file(f) for f in matches), [f.stem for f in matches]


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
