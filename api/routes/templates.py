"""
Template Library — Save/load campaign brief templates.
Templates are stored as JSON files in knowledge_base/_templates/
"""
import json
import logging
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config.settings import PROJECT_ROOT
from src.utils.paths import atomic_write_text, safe_join, validate_id

router = APIRouter()

logger = logging.getLogger(__name__)

TEMPLATES_DIR = PROJECT_ROOT / "knowledge_base" / "_templates"


def _template_path(template_id: str) -> Path:
    """Resolve file template, chặn path traversal qua template_id."""
    validate_id(template_id, "template_id")
    return safe_join(TEMPLATES_DIR, f"{template_id}.json")


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    brief: dict  # The campaign brief to save as template


@router.get("/")
def list_templates():
    """List all saved templates."""
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    templates = []
    for f in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            templates.append({
                "id": f.stem,
                "name": data.get("name", f.stem),
                "description": data.get("description", ""),
                "created_at": data.get("created_at", ""),
                "brief_summary": _summarize_brief(data.get("brief", {})),
            })
        except (OSError, ValueError) as e:
            logger.warning("Bỏ qua template hỏng %s: %s", f.name, e)
            continue
    return templates


@router.get("/{template_id}")
def get_template(template_id: str):
    """Get a single template with full brief data."""
    path = _template_path(template_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/")
def create_template(data: TemplateCreate):
    """Save current campaign brief as a template."""
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    template_id = str(uuid.uuid4())[:8]

    template = {
        "id": template_id,
        "name": data.name,
        "description": data.description,
        "brief": data.brief,
        "created_at": datetime.now().isoformat(),
    }

    path = _template_path(template_id)
    atomic_write_text(path, json.dumps(template, ensure_ascii=False, indent=2))
    return template


@router.delete("/{template_id}")
def delete_template(template_id: str):
    """Delete a template."""
    path = _template_path(template_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    path.unlink()
    return {"status": "deleted"}


def _summarize_brief(brief: dict) -> str:
    """Create a short summary of the brief for display."""
    parts = []
    if brief.get("goal"):
        parts.append(brief["goal"])
    offer = brief.get("offer", {})
    if offer.get("product_or_service"):
        parts.append(offer["product_or_service"])
    channels = brief.get("channels", [])
    if channels:
        parts.append(f"{len(channels)} channels")
    return " • ".join(parts) if parts else "Empty template"
