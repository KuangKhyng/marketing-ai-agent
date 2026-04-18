"""
Brand Management API routes.

CRUD operations for brands, documents, and voice profiles.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.knowledge.brand_manager import BrandManager

router = APIRouter()
manager = BrandManager()


# === Request Models ===

class CreateBrandRequest(BaseModel):
    id: str
    name: str
    description: str = ""
    color: str = "#6c5ce7"
    icon: str = "📦"


class UpdateBrandRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    default_channels: Optional[list[str]] = None
    default_goal: Optional[str] = None
    forbidden_claims: Optional[list[str]] = None
    mandatory_terms: Optional[list[str]] = None


class SaveDocumentRequest(BaseModel):
    content: str


class UpdateVoiceProfileRequest(BaseModel):
    profile: dict


# === Brand CRUD ===

@router.get("/")
def list_brands():
    """List all brands with metadata and completeness scores."""
    return manager.list_brands()


@router.get("/{brand_id}")
def get_brand(brand_id: str):
    """Get brand details including document list."""
    brand = manager.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


@router.post("/")
def create_brand(req: CreateBrandRequest):
    """Create a new brand with default template files."""
    if manager.get_brand(req.id):
        raise HTTPException(status_code=409, detail="Brand already exists")
    return manager.create_brand(req.id, req.name, req.description, req.color, req.icon)


@router.put("/{brand_id}")
def update_brand(brand_id: str, req: UpdateBrandRequest):
    """Update brand metadata."""
    result = manager.update_brand_meta(brand_id, req.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Brand not found")
    return result


@router.delete("/{brand_id}")
def delete_brand(brand_id: str):
    """Delete a brand and all its knowledge."""
    if not manager.delete_brand(brand_id):
        raise HTTPException(status_code=404, detail="Brand not found")
    return {"deleted": True}


# === Document CRUD ===

@router.get("/{brand_id}/docs/{doc_path:path}")
def get_document(brand_id: str, doc_path: str):
    """Get document content."""
    content = manager.get_document(brand_id, doc_path)
    if content is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"path": doc_path, "content": content}


@router.put("/{brand_id}/docs/{doc_path:path}")
def save_document(brand_id: str, doc_path: str, req: SaveDocumentRequest):
    """Create or update a document."""
    manager.save_document(brand_id, doc_path, req.content)
    return {"saved": True, "path": doc_path}


@router.delete("/{brand_id}/docs/{doc_path:path}")
def delete_document(brand_id: str, doc_path: str):
    """Delete a document."""
    if not manager.delete_document(brand_id, doc_path):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True}


# === Voice Profile ===

@router.get("/{brand_id}/voice-profile")
def get_voice_profile(brand_id: str):
    """Get voice profile for a brand."""
    profile = manager.get_voice_profile(brand_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    return profile


@router.put("/{brand_id}/voice-profile")
def update_voice_profile(brand_id: str, req: UpdateVoiceProfileRequest):
    """Update voice profile for a brand."""
    manager.update_voice_profile(brand_id, req.profile)
    return {"updated": True}


# === Knowledge Preview ===

@router.get("/{brand_id}/preview")
def get_knowledge_preview(brand_id: str):
    """Get full knowledge preview with token estimate."""
    preview = manager.get_knowledge_preview(brand_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Brand not found")
    return preview
