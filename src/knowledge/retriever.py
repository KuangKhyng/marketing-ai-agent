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
from pathlib import Path

from src.models.brief import CampaignBrief
from src.config.settings import PROJECT_ROOT

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge_base"
BRANDS_DIR = KNOWLEDGE_DIR / "brands"
GLOBAL_DIR = KNOWLEDGE_DIR / "_global"


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
    }

    # === ALWAYS LOAD: Global platform rules ===
    channels = [c.value for c in brief.channels]
    platforms_dir = GLOBAL_DIR / "platforms"
    if platforms_dir.exists():
        for channel in channels:
            filepath = platforms_dir / f"{channel}.md"
            if filepath.exists():
                context["platform_rules"][channel] = filepath.read_text(encoding="utf-8")

    # === ALWAYS LOAD: Global content policies ===
    policies_parts = []
    policies_dir = GLOBAL_DIR / "policies"
    if policies_dir.exists():
        for f in policies_dir.glob("*.md"):
            policies_parts.append(f.read_text(encoding="utf-8"))

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
                brand_parts.append(filepath.read_text(encoding="utf-8"))
        context["brand"] = "\n\n---\n\n".join(brand_parts)

        # Products — load all product files
        products_dir = brand_dir / "products"
        if products_dir.exists():
            product_parts = []
            for f in products_dir.glob("*.md"):
                product_parts.append(f.read_text(encoding="utf-8"))
            context["product"] = "\n\n---\n\n".join(product_parts)

        # Audience — load all audience files
        audience_dir = brand_dir / "audience"
        if audience_dir.exists():
            audience_parts = []
            for f in audience_dir.glob("*.md"):
                audience_parts.append(f.read_text(encoding="utf-8"))
            context["audience"] = "\n\n---\n\n".join(audience_parts)

        # Voice profile
        voice_path = brand_dir / "voice_profile.json"
        if voice_path.exists():
            context["voice_profile"] = json.loads(
                voice_path.read_text(encoding="utf-8")
            )
        else:
            context["voice_profile"] = _get_generic_voice_profile()

        # Brand-specific policies (merge with global)
        brand_policies_dir = brand_dir / "policies"
        if brand_policies_dir.exists():
            for f in brand_policies_dir.glob("*.md"):
                policies_parts.append(f.read_text(encoding="utf-8"))

        # Brand metadata (forbidden claims, mandatory terms)
        meta_path = brand_dir / "brand.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            context["brand_meta"] = meta

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
