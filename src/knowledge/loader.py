"""
Knowledge Base Loader — read markdown files from knowledge_base/ directory.

Phase 1: Static file loading.
Phase 2: Replace with ChromaDB RAG retrieval.
"""
import os
from pathlib import Path
from typing import Optional

from src.config.settings import PROJECT_ROOT

KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"


def load_knowledge_file(relative_path: str) -> str:
    """
    Load a single markdown file from the knowledge base.

    Args:
        relative_path: Path relative to knowledge_base/ directory.
            E.g., "brand/brand_identity.md"

    Returns:
        File contents as string.

    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    filepath = KNOWLEDGE_BASE_DIR / relative_path
    if not filepath.exists():
        raise FileNotFoundError(f"Knowledge file not found: {filepath}")
    return filepath.read_text(encoding="utf-8")


def load_all_brand_context() -> dict[str, str]:
    """
    Load all brand-related files from knowledge_base/brand/.

    Returns:
        Dict with keys like "brand_identity", "tone_of_voice", etc.
    """
    brand_dir = KNOWLEDGE_BASE_DIR / "brand"
    context = {}
    if brand_dir.exists():
        for filepath in brand_dir.glob("*.md"):
            key = filepath.stem  # e.g., "brand_identity"
            context[key] = filepath.read_text(encoding="utf-8")
    return context


def find_product_file(product_name: str) -> Optional[str]:
    """
    Find and load the best matching product file.

    Phase 1: Simple — load _template.md (or first .md file found).
    Phase 2: Use ChromaDB to semantic-match product_name.

    Args:
        product_name: Product/service name from the brief.

    Returns:
        Product file contents, or None if not found.
    """
    products_dir = KNOWLEDGE_BASE_DIR / "products"
    if not products_dir.exists():
        return None

    # Try exact match first (filename contains product name keywords)
    product_name_lower = product_name.lower()
    for filepath in products_dir.glob("*.md"):
        if filepath.stem.startswith("_"):
            continue  # skip templates for exact match
        if any(word in filepath.stem.lower() for word in product_name_lower.split()):
            return filepath.read_text(encoding="utf-8")

    # Fallback to _template.md
    template_path = products_dir / "_template.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")

    # Fallback to first .md file found
    for filepath in products_dir.glob("*.md"):
        return filepath.read_text(encoding="utf-8")

    return None


def load_audience_persona(persona_description: str) -> Optional[str]:
    """
    Load the best matching audience persona file.

    Phase 1: Simple — load _template.md.
    Phase 2: Use ChromaDB to semantic-match persona.

    Args:
        persona_description: Audience description from the brief.

    Returns:
        Persona file contents, or None if not found.
    """
    audience_dir = KNOWLEDGE_BASE_DIR / "audience"
    if not audience_dir.exists():
        return None

    # Try template first
    template_path = audience_dir / "_template.md"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")

    # Fallback to first .md file
    for filepath in audience_dir.glob("*.md"):
        return filepath.read_text(encoding="utf-8")

    return None


def load_platform_rules(channels: list[str]) -> dict[str, str]:
    """
    Load platform rules for specified channels.

    Args:
        channels: List of channel names, e.g., ["facebook", "instagram"]

    Returns:
        Dict mapping channel name to platform rules text.
    """
    platforms_dir = KNOWLEDGE_BASE_DIR / "platforms"
    rules = {}
    for channel in channels:
        filepath = platforms_dir / f"{channel}.md"
        if filepath.exists():
            rules[channel] = filepath.read_text(encoding="utf-8")
    return rules


def load_content_policies() -> str:
    """Load content policies from knowledge_base/policies/."""
    policies_dir = KNOWLEDGE_BASE_DIR / "policies"
    if not policies_dir.exists():
        return ""

    policies = []
    for filepath in policies_dir.glob("*.md"):
        policies.append(filepath.read_text(encoding="utf-8"))
    return "\n\n---\n\n".join(policies)
