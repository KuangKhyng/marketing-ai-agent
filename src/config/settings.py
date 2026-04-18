"""
Config settings — load .env, model configs, platform specs.
"""
import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Load .env file
load_dotenv(PROJECT_ROOT / ".env")


def get_api_key() -> str:
    """Get Anthropic API key from environment."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    key = key.strip()
    
    if not key:
        env_keys = list(os.environ.keys())
        has_anthropic = any("ANTHROPIC" in k.upper() for k in env_keys)
        raise ValueError(
            f"ANTHROPIC_API_KEY is empty or missing! (Debug: has_anthropic_in_env={has_anthropic}). "
            "Please ensure you clicked 'Redeploy' on Railway after adding the variable."
        )
        
    if key.startswith("sk-ant-..."):
        raise ValueError("API Key is still the placeholder text.")
        
    return key


def _load_yaml(filename: str) -> dict:
    """Load a YAML config file from the config directory."""
    config_dir = Path(__file__).resolve().parent
    filepath = config_dir / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# Cached configs
_models_config: Optional[dict] = None
_platforms_config: Optional[dict] = None


def get_models_config() -> dict:
    """Load and cache models.yaml."""
    global _models_config
    if _models_config is None:
        _models_config = _load_yaml("models.yaml")
    return _models_config


def get_platforms_config() -> dict:
    """Load and cache platforms.yaml."""
    global _platforms_config
    if _platforms_config is None:
        _platforms_config = _load_yaml("platforms.yaml")
    return _platforms_config


def get_model_config(node_name: str) -> dict[str, Any]:
    """
    Get model configuration for a specific node.

    Returns dict with keys: model, temperature, max_tokens.
    Returns empty dict if node has no model (e.g., context_builder).
    """
    config = get_models_config()
    node_config = config.get("nodes", {}).get(node_name, {})
    if node_config.get("model") is None:
        return {}
    return {
        "model": node_config["model"],
        "temperature": node_config.get("temperature", 0.5),
        "max_tokens": node_config.get("max_tokens", 2000),
    }


def get_platform_specs(platform: str, deliverable: str = None) -> dict:
    """
    Get platform specifications.

    Args:
        platform: e.g., "facebook", "instagram", "tiktok"
        deliverable: e.g., "post", "carousel", "reels_script"

    Returns platform spec dict.
    """
    config = get_platforms_config()
    platform_config = config.get(platform, {})
    if deliverable:
        return platform_config.get(deliverable, platform_config)
    return platform_config


# Cost constants (USD per 1M tokens)
COST_PER_1M = {
    "claude-haiku-4-5-20251001": {"input": 0.25, "output": 1.25},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for a single LLM call."""
    rates = COST_PER_1M.get(model, {"input": 3.0, "output": 15.0})
    cost = (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
    return round(cost, 6)
