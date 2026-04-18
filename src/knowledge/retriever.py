"""
Context Retriever — assemble context_pack from knowledge base.

Source-of-truth hierarchy (priority cao → thấp):
1. User input (brief.additional_context)
2. Brand policies (knowledge_base/policies/)
3. Brand identity (knowledge_base/brand/)
4. Product facts (knowledge_base/products/)
5. Audience personas (knowledge_base/audience/)
6. Platform rules (knowledge_base/platforms/)

Phase 1: Static file loading.
Phase 2: ChromaDB RAG retrieval with metadata filtering.
"""
from src.models.brief import CampaignBrief
from src.knowledge.loader import (
    load_all_brand_context,
    find_product_file,
    load_audience_persona,
    load_platform_rules,
    load_content_policies,
)
from src.knowledge.voice_analyzer import load_voice_profile


def build_context_pack(brief: CampaignBrief) -> dict:
    """
    Assemble the full context pack for a campaign brief.

    This is the primary function called by the context_builder node.

    Args:
        brief: Parsed CampaignBrief from brief_parser node.

    Returns:
        context_pack dict with keys:
        - brand: str (combined brand guidelines)
        - product: str (product/service information)
        - audience: str (audience persona)
        - platform_rules: dict[str, str] (per-channel rules)
        - policies: str (content policies)
        - voice_profile: dict (voice profile JSON)
        - additional_context: str (user-provided context, highest priority)
    """
    # 1. Brand context
    brand_context = load_all_brand_context()
    brand_text = "\n\n---\n\n".join(
        f"## {key.replace('_', ' ').title()}\n\n{value}"
        for key, value in brand_context.items()
    )

    # 2. Product info
    product_text = find_product_file(brief.offer.product_or_service) or ""

    # 3. Audience persona
    audience_text = load_audience_persona(brief.audience.persona_description) or ""

    # 4. Platform rules
    channel_names = [ch.value for ch in brief.channels]
    platform_rules = load_platform_rules(channel_names)

    # 5. Content policies
    policies_text = load_content_policies()

    # 6. Voice profile
    voice_profile = load_voice_profile(brief.brand.voice_profile_id)

    return {
        "brand": brand_text,
        "product": product_text,
        "audience": audience_text,
        "platform_rules": platform_rules,
        "policies": policies_text,
        "voice_profile": voice_profile,
        "additional_context": brief.additional_context or "",
    }
