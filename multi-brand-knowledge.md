# Marketing Agent — Multi-Brand Knowledge Management System

## Overview

Upgrade hệ thống knowledge từ hardcode 1 brand (TửViOnline) thành **multi-brand management system**:

- Mỗi brand có knowledge riêng biệt (brand identity, tone, products, audience, policies)
- UI cho phép quản lý knowledge: tạo brand, thêm/sửa/xóa documents
- Khi tạo campaign, user chọn brand → pipeline load đúng knowledge của brand đó
- Nếu không chọn brand → generic mode, pipeline viết tự do không dính brand nào

---

## 1. Data Architecture

### Cấu trúc thư mục mới

```
knowledge_base/
├── _global/                          # Shared across all brands
│   ├── platforms/
│   │   ├── facebook.md
│   │   ├── instagram.md
│   │   └── tiktok.md
│   └── policies/
│       └── content_policy.md
│
├── brands/
│   ├── tuvionline/                   # Brand A
│   │   ├── brand.json                # Brand metadata + config
│   │   ├── identity.md               # Brand identity
│   │   ├── tone_of_voice.md          # Tone guidelines
│   │   ├── visual_guidelines.md
│   │   ├── voice_profile.json        # Voice profile
│   │   ├── products/
│   │   │   ├── tu_vi_online.md
│   │   │   └── tu_vi_premium.md
│   │   ├── audience/
│   │   │   ├── gen_z_spiritual.md
│   │   │   └── millennials.md
│   │   └── policies/                 # Brand-specific policies (override global)
│   │       └── claims_policy.md
│   │
│   ├── coffee_shop/                  # Brand B
│   │   ├── brand.json
│   │   ├── identity.md
│   │   ├── tone_of_voice.md
│   │   ├── voice_profile.json
│   │   ├── products/
│   │   │   └── signature_drinks.md
│   │   └── audience/
│   │       └── young_professionals.md
│   │
│   └── ... (more brands)
```

### brand.json — Brand Metadata

Mỗi brand có 1 file `brand.json` chứa metadata:

```json
{
  "id": "tuvionline",
  "name": "TửViOnline",
  "description": "Nền tảng xem tử vi online cho Gen Z",
  "created_at": "2026-04-18",
  "updated_at": "2026-04-18",
  "color": "#6c5ce7",
  "icon": "✦",
  "default_channels": ["facebook", "instagram"],
  "default_goal": "awareness",
  "voice_profile_id": "default",
  "forbidden_claims": [
    "cam kết kết quả chắc chắn",
    "tiên tri tương lai"
  ],
  "mandatory_terms": []
}
```

---

## 2. Backend Changes

### 2.1 New: Brand Manager — `src/knowledge/brand_manager.py`

```python
"""
Brand Manager — CRUD operations for multi-brand knowledge base.
"""
import json
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.config.settings import PROJECT_ROOT

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge_base"
BRANDS_DIR = KNOWLEDGE_DIR / "brands"
GLOBAL_DIR = KNOWLEDGE_DIR / "_global"


class BrandManager:
    """Manages brand knowledge base operations."""

    def list_brands(self) -> list[dict]:
        """List all brands with metadata."""
        brands = []
        if not BRANDS_DIR.exists():
            return brands

        for brand_dir in sorted(BRANDS_DIR.iterdir()):
            if brand_dir.is_dir() and not brand_dir.name.startswith("_"):
                meta = self._load_brand_meta(brand_dir.name)
                if meta:
                    # Count documents
                    doc_count = sum(1 for f in brand_dir.rglob("*.md"))
                    meta["document_count"] = doc_count
                    brands.append(meta)
        return brands

    def get_brand(self, brand_id: str) -> Optional[dict]:
        """Get brand metadata + list of all documents."""
        brand_dir = BRANDS_DIR / brand_id
        if not brand_dir.exists():
            return None

        meta = self._load_brand_meta(brand_id)
        if not meta:
            return None

        # List all documents
        documents = []
        for md_file in sorted(brand_dir.rglob("*.md")):
            rel_path = md_file.relative_to(brand_dir)
            category = rel_path.parts[0] if len(rel_path.parts) > 1 else "general"
            documents.append({
                "path": str(rel_path),
                "category": category,
                "name": md_file.stem.replace("_", " ").title(),
                "size": md_file.stat().st_size,
                "updated_at": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat(),
            })

        meta["documents"] = documents
        return meta

    def create_brand(self, brand_id: str, name: str, description: str = "",
                     color: str = "#6c5ce7", icon: str = "📦") -> dict:
        """Create a new brand with default structure."""
        brand_dir = BRANDS_DIR / brand_id
        brand_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (brand_dir / "products").mkdir(exist_ok=True)
        (brand_dir / "audience").mkdir(exist_ok=True)

        # Create brand.json
        meta = {
            "id": brand_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "color": color,
            "icon": icon,
            "default_channels": ["facebook", "instagram"],
            "default_goal": "awareness",
            "forbidden_claims": [],
            "mandatory_terms": [],
        }
        self._save_brand_meta(brand_id, meta)

        # Create default empty files
        (brand_dir / "identity.md").write_text(
            f"# {name}\n\n## Brand Identity\n\n(Thêm brand identity tại đây)\n",
            encoding="utf-8",
        )
        (brand_dir / "tone_of_voice.md").write_text(
            f"# Tone of Voice — {name}\n\n## Overall Tone\n\n(Mô tả tone tại đây)\n",
            encoding="utf-8",
        )

        # Create default voice profile
        voice_profile = {
            "profile_id": brand_id,
            "tone": {"primary": "friendly", "secondary": "professional", "formality": 0.5},
            "writing_style": {"avg_sentence_length": 15, "perspective": "second_person"},
            "vocabulary": {"preferred": [], "avoided": [], "emoji_style": "moderate"},
            "anti_ai_rules": [
                "Never start with 'Bạn đã bao giờ'",
                "Avoid 'Trong thế giới hiện đại'",
            ],
        }
        (brand_dir / "voice_profile.json").write_text(
            json.dumps(voice_profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return meta

    def delete_brand(self, brand_id: str) -> bool:
        """Delete a brand and all its knowledge."""
        brand_dir = BRANDS_DIR / brand_id
        if brand_dir.exists():
            shutil.rmtree(brand_dir)
            return True
        return False

    def update_brand_meta(self, brand_id: str, updates: dict) -> Optional[dict]:
        """Update brand metadata (name, description, color, etc.)."""
        meta = self._load_brand_meta(brand_id)
        if not meta:
            return None

        allowed_fields = ["name", "description", "color", "icon",
                          "default_channels", "default_goal",
                          "forbidden_claims", "mandatory_terms"]
        for key, value in updates.items():
            if key in allowed_fields:
                meta[key] = value

        meta["updated_at"] = datetime.now().isoformat()
        self._save_brand_meta(brand_id, meta)
        return meta

    # === Document operations ===

    def get_document(self, brand_id: str, doc_path: str) -> Optional[str]:
        """Get document content."""
        file_path = BRANDS_DIR / brand_id / doc_path
        if file_path.exists() and file_path.suffix == ".md":
            return file_path.read_text(encoding="utf-8")
        return None

    def save_document(self, brand_id: str, doc_path: str, content: str) -> bool:
        """Create or update a document."""
        file_path = BRANDS_DIR / brand_id / doc_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if not doc_path.endswith(".md"):
            doc_path += ".md"
            file_path = BRANDS_DIR / brand_id / doc_path

        file_path.write_text(content, encoding="utf-8")

        # Update brand modified time
        meta = self._load_brand_meta(brand_id)
        if meta:
            meta["updated_at"] = datetime.now().isoformat()
            self._save_brand_meta(brand_id, meta)

        return True

    def delete_document(self, brand_id: str, doc_path: str) -> bool:
        """Delete a document."""
        file_path = BRANDS_DIR / brand_id / doc_path
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def update_voice_profile(self, brand_id: str, profile: dict) -> bool:
        """Update voice profile for a brand."""
        file_path = BRANDS_DIR / brand_id / "voice_profile.json"
        file_path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True

    def get_voice_profile(self, brand_id: str) -> Optional[dict]:
        """Get voice profile for a brand."""
        file_path = BRANDS_DIR / brand_id / "voice_profile.json"
        if file_path.exists():
            return json.loads(file_path.read_text(encoding="utf-8"))
        return None

    # === Internal helpers ===

    def _load_brand_meta(self, brand_id: str) -> Optional[dict]:
        meta_path = BRANDS_DIR / brand_id / "brand.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))
        return None

    def _save_brand_meta(self, brand_id: str, meta: dict):
        meta_path = BRANDS_DIR / brand_id / "brand.json"
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
```

### 2.2 Sửa `src/knowledge/retriever.py` — Brand-aware context loading

```python
"""
Retriever — brand-aware context assembly.
"""
import json
from pathlib import Path
from src.config.settings import PROJECT_ROOT
from src.knowledge.loader import load_platform_rules, load_content_policies

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge_base"
BRANDS_DIR = KNOWLEDGE_DIR / "brands"
GLOBAL_DIR = KNOWLEDGE_DIR / "_global"


def build_context_pack(brief, brand_id: str = None) -> dict:
    """
    Assemble context pack.

    Args:
        brief: CampaignBrief
        brand_id: Brand ID to load knowledge from. None = generic mode.

    Returns:
        Context pack dict.
    """
    context = {
        "brand": "",
        "product": "",
        "audience": "",
        "platform_rules": {},
        "policies": "",
        "voice_profile": {},
        "brand_id": brand_id or "",
        "mode": "branded" if brand_id else "generic",
    }

    # === ALWAYS LOAD (global) ===
    channels = [c.value for c in brief.channels]

    # Platform rules — load from _global/platforms/
    platforms_dir = GLOBAL_DIR / "platforms"
    if platforms_dir.exists():
        for channel in channels:
            filepath = platforms_dir / f"{channel}.md"
            if filepath.exists():
                context["platform_rules"][channel] = filepath.read_text(encoding="utf-8")

    # Global content policies
    policies_dir = GLOBAL_DIR / "policies"
    if policies_dir.exists():
        policies = []
        for f in policies_dir.glob("*.md"):
            policies.append(f.read_text(encoding="utf-8"))
        context["policies"] = "\n\n---\n\n".join(policies)

    # === BRAND-SPECIFIC (only if brand_id provided) ===
    if brand_id:
        brand_dir = BRANDS_DIR / brand_id
        if not brand_dir.exists():
            # Brand not found — fall back to generic
            context["mode"] = "generic"
            context["voice_profile"] = _get_generic_voice_profile()
            return context

        # Brand identity + tone
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
            context["voice_profile"] = json.loads(voice_path.read_text(encoding="utf-8"))
        else:
            context["voice_profile"] = _get_generic_voice_profile()

        # Brand-specific policies (merge with global)
        brand_policies_dir = brand_dir / "policies"
        if brand_policies_dir.exists():
            for f in brand_policies_dir.glob("*.md"):
                context["policies"] += "\n\n---\n\n" + f.read_text(encoding="utf-8")

        # Brand metadata (forbidden claims, mandatory terms)
        meta_path = brand_dir / "brand.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            context["brand_meta"] = meta
    else:
        # === GENERIC MODE ===
        context["voice_profile"] = _get_generic_voice_profile()
        context["audience"] = f"Target audience: {brief.audience.persona_description}"

    return context


def _get_generic_voice_profile() -> dict:
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
```

### 2.3 Sửa `src/nodes/context_builder.py` — truyền brand_id

```python
def context_builder_node(state: dict) -> dict:
    if state.get("error"):
        return {"current_node": "context_builder"}

    node_trace = NodeTrace(
        node_name="context_builder",
        started_at=datetime.now(),
    )

    try:
        brief = state["brief"]
        brand_id = state.get("brand_id")  # NEW: passed from initial state

        context_pack = build_context_pack(brief, brand_id=brand_id)

        node_trace.output_summary = f"Mode: {context_pack['mode']}, brand: {brand_id or 'generic'}"
        node_trace.finished_at = datetime.now()

        return {
            "context_pack": context_pack,
            "current_node": "context_builder",
            "trace": update_trace(state, node_trace),
        }
    except Exception as e:
        # ... error handling unchanged
```

### 2.4 Sửa `src/graph/state.py` — thêm brand_id

```python
class CampaignState(TypedDict):
    raw_input: str
    brand_id: Optional[str]             # NEW: selected brand ID, None = generic
    brief: Optional[CampaignBrief]
    context_pack: Optional[dict]
    # ... rest unchanged
```

### 2.5 New API routes — `api/routes/brands.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.knowledge.brand_manager import BrandManager

router = APIRouter()
manager = BrandManager()


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
    forbidden_claims: Optional[list[str]] = None
    mandatory_terms: Optional[list[str]] = None


class SaveDocumentRequest(BaseModel):
    content: str


class UpdateVoiceProfileRequest(BaseModel):
    profile: dict


# === Brand CRUD ===

@router.get("/")
def list_brands():
    """List all brands."""
    return manager.list_brands()


@router.get("/{brand_id}")
def get_brand(brand_id: str):
    """Get brand details + document list."""
    brand = manager.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


@router.post("/")
def create_brand(req: CreateBrandRequest):
    """Create a new brand."""
    # Check if already exists
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
    profile = manager.get_voice_profile(brand_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    return profile


@router.put("/{brand_id}/voice-profile")
def update_voice_profile(brand_id: str, req: UpdateVoiceProfileRequest):
    manager.update_voice_profile(brand_id, req.profile)
    return {"updated": True}
```

### 2.6 Register brand routes in `api/main.py`

```python
from api.routes.brands import router as brands_router

app.include_router(brands_router, prefix="/api/brands", tags=["brands"])
```

### 2.7 Sửa `api/schemas.py` — thêm brand_id vào CampaignInput

```python
class CampaignInput(BaseModel):
    mode: str = "free_text"
    raw_input: Optional[str] = None
    brand_id: Optional[str] = None     # NEW: None = generic mode

    # structured mode fields...
    goal: Optional[str] = None
    product: Optional[str] = None
    audience: Optional[str] = None
    channels: Optional[list[str]] = None
    key_message: Optional[str] = None
    cta: Optional[str] = None
```

### 2.8 Sửa `api/routes/campaign.py` — pass brand_id

```python
@router.post("/start", response_model=PipelineStatus)
def start_campaign(input: CampaignInput):
    runner = PipelineRunner()
    raw_input = input.to_raw_input()

    # Pass brand_id to pipeline
    state = runner.phase_1_parse(raw_input, brand_id=input.brand_id)
    # ...
```

### 2.9 Sửa `api/pipeline_runner.py` — accept brand_id

```python
class PipelineRunner:
    def __init__(self):
        self.state = None

    def phase_1_parse(self, raw_input: str, brand_id: str = None) -> dict:
        self.state = self._init_state(raw_input, brand_id)
        # ... rest unchanged

    def _init_state(self, raw_input: str, brand_id: str = None) -> dict:
        return {
            "raw_input": raw_input,
            "brand_id": brand_id,       # NEW
            # ... rest unchanged
        }
```

### 2.10 Migrate existing knowledge_base

Script để migrate từ cấu trúc cũ sang mới:

```python
# scripts/migrate_knowledge.py
import shutil
from pathlib import Path

old_kb = Path("knowledge_base")
new_kb = Path("knowledge_base_new")

# Create _global
(new_kb / "_global" / "platforms").mkdir(parents=True, exist_ok=True)
(new_kb / "_global" / "policies").mkdir(parents=True, exist_ok=True)

# Move platform files
for f in (old_kb / "platforms").glob("*.md"):
    shutil.copy(f, new_kb / "_global" / "platforms" / f.name)

# Move policies
for f in (old_kb / "policies").glob("*.md"):
    shutil.copy(f, new_kb / "_global" / "policies" / f.name)

# Create tuvionline brand
brand_dir = new_kb / "brands" / "tuvionline"
brand_dir.mkdir(parents=True, exist_ok=True)
(brand_dir / "products").mkdir(exist_ok=True)
(brand_dir / "audience").mkdir(exist_ok=True)

# Move brand files
for f in (old_kb / "brand").glob("*.md"):
    if f.stem == "brand_identity":
        shutil.copy(f, brand_dir / "identity.md")
    else:
        shutil.copy(f, brand_dir / f.name)

# Move products
for f in (old_kb / "products").glob("*.md"):
    shutil.copy(f, brand_dir / "products" / f.name)

# Move audience
for f in (old_kb / "audience").glob("*.md"):
    shutil.copy(f, brand_dir / "audience" / f.name)

# Move voice profile
shutil.copy("voice_profiles/default.json", brand_dir / "voice_profile.json")

# Create brand.json
import json
(brand_dir / "brand.json").write_text(json.dumps({
    "id": "tuvionline",
    "name": "TửViOnline",
    "description": "Nền tảng xem tử vi online cho Gen Z",
    "created_at": "2026-04-18",
    "updated_at": "2026-04-18",
    "color": "#6c5ce7",
    "icon": "✦",
    "default_channels": ["facebook", "instagram"],
    "default_goal": "awareness",
    "forbidden_claims": ["cam kết kết quả chắc chắn", "tiên tri tương lai"],
    "mandatory_terms": [],
}, ensure_ascii=False, indent=2))

print("Migration complete!")
print(f"Old: {old_kb}")
print(f"New: {new_kb}")
print("Review new structure, then rename:")
print("  mv knowledge_base knowledge_base_old")
print("  mv knowledge_base_new knowledge_base")
```

---

## 3. Frontend — Brand Management UI

### 3.1 Thêm trang Brand Management

```
web/src/pages/
├── BrandsPage.jsx              # List all brands
├── BrandDetailPage.jsx         # View/edit brand + documents
└── ... (existing pages)
```

### 3.2 BrandsPage.jsx — Quản lý brands

```jsx
import { useState, useEffect } from 'react';
import { campaignAPI } from '../api/client';
import { Plus, Trash2, Edit, FolderOpen } from 'lucide-react';

export default function BrandsPage() {
  const [brands, setBrands] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newBrand, setNewBrand] = useState({ id: '', name: '', description: '' });

  useEffect(() => {
    loadBrands();
  }, []);

  const loadBrands = async () => {
    const { data } = await api.get('/brands/');
    setBrands(data);
  };

  const createBrand = async () => {
    await api.post('/brands/', newBrand);
    setShowCreate(false);
    setNewBrand({ id: '', name: '', description: '' });
    loadBrands();
  };

  const deleteBrand = async (id) => {
    if (!confirm(`Xóa brand "${id}" và tất cả knowledge? Không thể hoàn tác!`)) return;
    await api.delete(`/brands/${id}`);
    loadBrands();
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">Knowledge Base</h2>
          <p style={{ color: 'var(--text-muted)' }}>Quản lý brand knowledge cho campaigns</p>
        </div>
        <button onClick={() => setShowCreate(true)}
                className="px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2"
                style={{ backgroundColor: 'var(--primary)', color: '#fff' }}>
          <Plus className="w-4 h-4" /> Thêm Brand
        </button>
      </div>

      {/* Create brand modal */}
      {showCreate && (
        <div className="rounded-xl p-6 mb-6" style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}>
          <h3 className="text-lg font-semibold mb-4">Tạo Brand Mới</h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Brand ID (không dấu, lowercase)</label>
              <input value={newBrand.id} onChange={e => setNewBrand({...newBrand, id: e.target.value.toLowerCase().replace(/\s/g, '_')})}
                     placeholder="coffee_shop"
                     className="w-full p-3 rounded-xl text-sm"
                     style={{ backgroundColor: 'var(--surface-light)', color: 'var(--text)', border: 'none' }} />
            </div>
            <div>
              <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Tên hiển thị</label>
              <input value={newBrand.name} onChange={e => setNewBrand({...newBrand, name: e.target.value})}
                     placeholder="Coffee Shop ABC"
                     className="w-full p-3 rounded-xl text-sm"
                     style={{ backgroundColor: 'var(--surface-light)', color: 'var(--text)', border: 'none' }} />
            </div>
          </div>
          <div className="mb-4">
            <label className="text-xs mb-1 block" style={{ color: 'var(--text-muted)' }}>Mô tả</label>
            <input value={newBrand.description} onChange={e => setNewBrand({...newBrand, description: e.target.value})}
                   placeholder="Quán cà phê specialty tại quận 1"
                   className="w-full p-3 rounded-xl text-sm"
                   style={{ backgroundColor: 'var(--surface-light)', color: 'var(--text)', border: 'none' }} />
          </div>
          <div className="flex gap-2">
            <button onClick={createBrand}
                    className="px-4 py-2 rounded-xl text-sm font-medium"
                    style={{ backgroundColor: 'var(--success)', color: '#fff' }}>
              Tạo
            </button>
            <button onClick={() => setShowCreate(false)}
                    className="px-4 py-2 rounded-xl text-sm"
                    style={{ backgroundColor: 'var(--surface-light)', color: 'var(--text-muted)' }}>
              Hủy
            </button>
          </div>
        </div>
      )}

      {/* Brand list */}
      <div className="grid grid-cols-1 gap-3">
        {brands.map(brand => (
          <div key={brand.id}
               className="rounded-xl p-5 flex items-center justify-between transition-all hover:brightness-110 cursor-pointer"
               style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}
               onClick={() => window.location.hash = `#/brands/${brand.id}`}>
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
                   style={{ backgroundColor: brand.color + '20', color: brand.color }}>
                {brand.icon}
              </div>
              <div>
                <h3 className="font-semibold">{brand.name}</h3>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {brand.description} · {brand.document_count} documents
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={e => { e.stopPropagation(); deleteBrand(brand.id); }}
                      className="p-2 rounded-lg hover:bg-red-500/20 transition-colors"
                      style={{ color: 'var(--error)' }}>
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}

        {brands.length === 0 && (
          <div className="text-center py-12 rounded-xl" style={{ backgroundColor: 'var(--surface)' }}>
            <p style={{ color: 'var(--text-muted)' }}>Chưa có brand nào. Tạo brand đầu tiên để bắt đầu!</p>
          </div>
        )}
      </div>
    </div>
  );
}
```

### 3.3 BrandDetailPage.jsx — Xem/sửa documents

```jsx
// Trang chi tiết brand:
// - Hiện list documents dạng tree (identity.md, tone.md, products/*, audience/*)
// - Click document → mở markdown editor
// - Nút "Add Document" → chọn category (products/audience/general) → nhập tên → editor
// - Nút "Delete Document"
// - Tab "Voice Profile" → JSON editor cho voice profile
// - Tab "Settings" → edit brand metadata (name, color, forbidden_claims, etc.)
```

### 3.4 Sửa InputPage.jsx — Brand Selector

```jsx
// Trong InputPage, thêm brand selector trước form:

const [brands, setBrands] = useState([]);
const [selectedBrand, setSelectedBrand] = useState(null); // null = generic

useEffect(() => {
  api.get('/brands/').then(res => setBrands(res.data));
}, []);

// UI:
<div className="mb-6">
  <label className="text-xs font-medium mb-2 block" style={{ color: 'var(--text-muted)' }}>
    Brand Knowledge
  </label>
  <div className="flex gap-2 flex-wrap">
    {/* Generic option */}
    <button onClick={() => setSelectedBrand(null)}
            className="px-4 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-all"
            style={{
              backgroundColor: !selectedBrand ? 'var(--primary)' : 'var(--surface)',
              color: !selectedBrand ? '#fff' : 'var(--text-muted)',
              border: !selectedBrand ? 'none' : '1px solid var(--border)',
            }}>
      🌐 Không có brand (Generic)
    </button>

    {/* Brand options */}
    {brands.map(brand => (
      <button key={brand.id}
              onClick={() => setSelectedBrand(brand.id)}
              className="px-4 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-all"
              style={{
                backgroundColor: selectedBrand === brand.id ? brand.color : 'var(--surface)',
                color: selectedBrand === brand.id ? '#fff' : 'var(--text-muted)',
                border: selectedBrand === brand.id ? 'none' : '1px solid var(--border)',
              }}>
        {brand.icon} {brand.name}
      </button>
    ))}

    {/* Add new brand shortcut */}
    <button onClick={() => navigate('/brands')}
            className="px-4 py-2.5 rounded-xl text-sm flex items-center gap-1"
            style={{ color: 'var(--text-muted)', border: '1px dashed var(--border)' }}>
      + Thêm brand
    </button>
  </div>
</div>

// Khi submit, pass brand_id:
const handleSubmit = async () => {
  const input = {
    ...formData,
    brand_id: selectedBrand,  // null nếu generic
  };
  const { data } = await campaignAPI.start(input);
  // ...
};
```

### 3.5 Sidebar — thêm navigation link

```jsx
// Trong Layout hoặc Sidebar, thêm link đến Brand Management:
<div className="mt-auto p-4 space-y-2">
  <button onClick={() => navigate('/brands')}
          className="w-full py-2 rounded-lg text-sm font-medium text-left px-3 flex items-center gap-2"
          style={{ color: 'var(--text-muted)' }}>
    📚 Knowledge Base
  </button>
  <button onClick={onReset}
          className="w-full py-2 rounded-lg text-sm font-medium text-left px-3 flex items-center gap-2"
          style={{ color: 'var(--text-muted)' }}>
    + New Campaign
  </button>
</div>
```

---

## 4. Sửa prompt templates cho brand-aware behavior

Tất cả prompt templates cần thêm section:

```markdown
## Context Mode

Bạn sẽ nhận context pack với field "mode":
- "branded": có brand context, voice profile, product info → PHẢI tuân thủ brand guidelines
- "generic": KHÔNG có brand context → viết tự do, tập trung vào topic user yêu cầu

**Nếu mode = "generic":**
- KHÔNG tự bịa brand name
- KHÔNG reference brand guidelines
- Viết dựa trên offer, audience, và platform rules
- Tone mặc định: friendly, engaging
```

---

## 5. Implementation Order

1. Chạy migration script — chuyển knowledge_base sang cấu trúc mới (5 phút)
2. Implement `brand_manager.py` (15 phút)
3. Sửa `retriever.py` — brand-aware loading (10 phút)
4. Sửa `state.py` + `context_builder.py` — pass brand_id (5 phút)
5. Implement `api/routes/brands.py` (10 phút)
6. Sửa `api/routes/campaign.py` + schemas — brand_id (5 phút)
7. Frontend: BrandsPage + BrandDetailPage (1-2 giờ)
8. Frontend: Brand selector trong InputPage (30 phút)
9. Sửa tất cả prompt templates (15 phút)
10. Test:
    - Tạo brand mới từ UI
    - Thêm documents cho brand
    - Chạy campaign VỚI brand → phải load brand context
    - Chạy campaign KHÔNG brand → phải viết generic, KHÔNG dính brand nào

---

## Expected Behavior

```
Scenario 1: Chọn brand "TửViOnline"
Input: "Tạo campaign awareness cho Gen Z"
→ Load knowledge từ brands/tuvionline/
→ Output: content có brand voice TửViOnline, reference tử vi

Scenario 2: Chọn brand "Coffee Shop"
Input: "Campaign khuyến mãi đồ uống mới"
→ Load knowledge từ brands/coffee_shop/
→ Output: content có brand voice Coffee Shop, reference đồ uống

Scenario 3: Không chọn brand (Generic)
Input: "Làm sao để có trái tim của một cô gái"
→ KHÔNG load brand knowledge nào
→ Output: content thuần về chủ đề tình cảm, không dính brand nào

Scenario 4: Không chọn brand (Generic)
Input: "Content marketing cho tiệm nail"
→ KHÔNG load brand knowledge nào
→ Output: content về tiệm nail, generic voice
```
