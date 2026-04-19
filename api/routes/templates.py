"""
Template Library — Save/load campaign brief templates.
Templates are stored as JSON files in knowledge_base/_templates/
"""
import json
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.config.settings import PROJECT_ROOT

router = APIRouter()

TEMPLATES_DIR = PROJECT_ROOT / "knowledge_base" / "_templates"


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    brief: dict  # The campaign brief to save as template


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


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
        except Exception:
            continue
    return templates


@router.get("/{template_id}")
def get_template(template_id: str):
    """Get a single template with full brief data."""
    path = TEMPLATES_DIR / f"{template_id}.json"
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

    path = TEMPLATES_DIR / f"{template_id}.json"
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    return template


@router.delete("/{template_id}")
def delete_template(template_id: str):
    """Delete a template."""
    path = TEMPLATES_DIR / f"{template_id}.json"
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
