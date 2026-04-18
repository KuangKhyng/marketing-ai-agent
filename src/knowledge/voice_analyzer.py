"""
Voice Analyzer — load voice profiles and (Phase 2) analyze sample posts.

Phase 1: Load existing voice profile JSON files.
Phase 2: Analyze sample posts to generate new voice profiles using LLM.
"""
import json
from pathlib import Path
from typing import Optional

from src.config.settings import PROJECT_ROOT

VOICE_PROFILES_DIR = PROJECT_ROOT / "voice_profiles"


def load_voice_profile(profile_id: str = "default") -> dict:
    """
    Load a voice profile JSON file.

    Args:
        profile_id: Profile identifier. Maps to voice_profiles/{profile_id}.json

    Returns:
        Voice profile dict.

    Raises:
        FileNotFoundError: If profile doesn't exist.
    """
    filepath = VOICE_PROFILES_DIR / f"{profile_id}.json"
    if not filepath.exists():
        # Fallback to default
        filepath = VOICE_PROFILES_DIR / "default.json"
        if not filepath.exists():
            raise FileNotFoundError(
                f"Voice profile '{profile_id}' not found and no default profile exists."
            )

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_voice_profile(profile_id: str, profile_data: dict) -> Path:
    """
    Save a voice profile to JSON file.

    Args:
        profile_id: Profile identifier.
        profile_data: Voice profile dict.

    Returns:
        Path to saved file.
    """
    VOICE_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    filepath = VOICE_PROFILES_DIR / f"{profile_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, ensure_ascii=False, indent=2)
    return filepath


# Phase 2 placeholder
def analyze_posts(posts: list[str], profile_id: str = "custom") -> dict:
    """
    Analyze sample posts to generate a voice profile.

    Phase 2: Will use Claude to analyze writing patterns, tone,
    vocabulary preferences, etc. from sample posts.

    Args:
        posts: List of sample post texts to analyze.
        profile_id: ID to assign to the generated profile.

    Returns:
        Generated voice profile dict.
    """
    raise NotImplementedError(
        "Voice analysis from sample posts is a Phase 2 feature. "
        "For now, manually create voice profiles in voice_profiles/ directory."
    )
