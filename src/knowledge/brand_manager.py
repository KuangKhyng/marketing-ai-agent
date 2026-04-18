"""
Brand Manager — CRUD operations for multi-brand knowledge base.

Each brand lives in knowledge_base/brands/{brand_id}/ with:
  - brand.json        (metadata)
  - identity.md       (brand identity)
  - tone_of_voice.md  (tone guidelines)
  - visual_guidelines.md
  - voice_profile.json
  - products/*.md
  - audience/*.md
  - policies/*.md
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
        """List all brands with metadata and document counts."""
        brands = []
        if not BRANDS_DIR.exists():
            return brands

        for brand_dir in sorted(BRANDS_DIR.iterdir()):
            if brand_dir.is_dir() and not brand_dir.name.startswith("_"):
                meta = self._load_brand_meta(brand_dir.name)
                if meta:
                    doc_count = sum(1 for f in brand_dir.rglob("*.md"))
                    meta["document_count"] = doc_count
                    meta["completeness"] = self._calc_completeness(brand_dir)
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

        # List all documents grouped by category
        documents = []
        for md_file in sorted(brand_dir.rglob("*.md")):
            rel_path = md_file.relative_to(brand_dir)
            category = self._categorize_doc(rel_path)
            documents.append({
                "path": str(rel_path).replace("\\", "/"),
                "category": category,
                "name": md_file.stem.replace("_", " ").title(),
                "size": md_file.stat().st_size,
                "updated_at": datetime.fromtimestamp(
                    md_file.stat().st_mtime
                ).isoformat(),
            })

        meta["documents"] = documents
        meta["completeness"] = self._calc_completeness(brand_dir)
        return meta

    def create_brand(
        self,
        brand_id: str,
        name: str,
        description: str = "",
        color: str = "#6c5ce7",
        icon: str = "📦",
    ) -> dict:
        """Create a new brand with default template files."""
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

        # Create default template files
        (brand_dir / "identity.md").write_text(
            f"# {name}\n\n## Brand Identity\n\n(Thêm brand identity tại đây)\n\n"
            f"## Mission\n\n(Sứ mệnh)\n\n"
            f"## Unique Selling Proposition (USP)\n\n(Điều gì khiến brand khác biệt)\n\n"
            f"## Brand Values\n\n- (Giá trị 1)\n- (Giá trị 2)\n",
            encoding="utf-8",
        )
        (brand_dir / "tone_of_voice.md").write_text(
            f"# Tone of Voice — {name}\n\n## Overall Tone\n\n(Mô tả tone tại đây)\n\n"
            f"## Do's\n\n- (Nên viết kiểu gì)\n\n"
            f"## Don'ts\n\n- (Không viết kiểu gì)\n",
            encoding="utf-8",
        )

        # Create default voice profile
        voice_profile = {
            "profile_id": brand_id,
            "tone": {
                "primary": "friendly",
                "secondary": "professional",
                "formality": 0.5,
            },
            "writing_style": {
                "avg_sentence_length": 15,
                "perspective": "second_person",
            },
            "vocabulary": {
                "preferred": [],
                "avoided": [],
                "emoji_style": "moderate",
                "common_emojis": [],
            },
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

        allowed_fields = [
            "name", "description", "color", "icon",
            "default_channels", "default_goal",
            "forbidden_claims", "mandatory_terms",
        ]
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
        if not doc_path.endswith(".md"):
            doc_path += ".md"

        file_path = BRANDS_DIR / brand_id / doc_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
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

    # === Voice Profile ===

    def get_voice_profile(self, brand_id: str) -> Optional[dict]:
        """Get voice profile for a brand."""
        file_path = BRANDS_DIR / brand_id / "voice_profile.json"
        if file_path.exists():
            return json.loads(file_path.read_text(encoding="utf-8"))
        return None

    def update_voice_profile(self, brand_id: str, profile: dict) -> bool:
        """Update voice profile for a brand."""
        file_path = BRANDS_DIR / brand_id / "voice_profile.json"
        if not file_path.parent.exists():
            return False
        file_path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True

    # === Knowledge Preview ===

    def get_knowledge_preview(self, brand_id: str) -> Optional[dict]:
        """Get full knowledge preview with token estimate."""
        brand_dir = BRANDS_DIR / brand_id
        if not brand_dir.exists():
            return None

        sections = {}
        total_size = 0

        # Identity
        for name in ["identity.md", "tone_of_voice.md", "visual_guidelines.md"]:
            path = brand_dir / name
            if path.exists():
                content = path.read_text(encoding="utf-8")
                sections[name.replace(".md", "")] = content
                total_size += len(content)

        # Products
        products_dir = brand_dir / "products"
        if products_dir.exists():
            product_texts = []
            for f in products_dir.glob("*.md"):
                content = f.read_text(encoding="utf-8")
                product_texts.append(content)
                total_size += len(content)
            if product_texts:
                sections["products"] = "\n\n---\n\n".join(product_texts)

        # Audience
        audience_dir = brand_dir / "audience"
        if audience_dir.exists():
            audience_texts = []
            for f in audience_dir.glob("*.md"):
                content = f.read_text(encoding="utf-8")
                audience_texts.append(content)
                total_size += len(content)
            if audience_texts:
                sections["audience"] = "\n\n---\n\n".join(audience_texts)

        # Voice profile
        voice_path = brand_dir / "voice_profile.json"
        if voice_path.exists():
            vp = json.loads(voice_path.read_text(encoding="utf-8"))
            sections["voice_profile"] = vp

        # Estimate tokens (rough: 1 token ≈ 3 bytes for Vietnamese)
        estimated_tokens = total_size // 3

        return {
            "sections": sections,
            "total_size_bytes": total_size,
            "estimated_tokens": estimated_tokens,
            "context_usage_percent": round(estimated_tokens / 150000 * 100, 1),
        }

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

    def _categorize_doc(self, rel_path: Path) -> str:
        """Categorize a document by its relative path."""
        parts = rel_path.parts
        if len(parts) > 1:
            return parts[0]  # "products", "audience", "policies"
        stem = rel_path.stem
        if stem in ("identity", "tone_of_voice", "visual_guidelines"):
            return "brand_core"
        return "general"

    def _calc_completeness(self, brand_dir: Path) -> dict:
        """Calculate knowledge completeness (4 dimensions × 25%)."""
        checks = {
            "identity": (brand_dir / "identity.md").exists()
                and len((brand_dir / "identity.md").read_text(encoding="utf-8").strip()) > 50,
            "tone": (brand_dir / "tone_of_voice.md").exists()
                and len((brand_dir / "tone_of_voice.md").read_text(encoding="utf-8").strip()) > 50,
            "product": any(
                f.stem != "_template"
                for f in (brand_dir / "products").glob("*.md")
            ) if (brand_dir / "products").exists() else False,
            "audience": any(
                f.stem != "_template"
                for f in (brand_dir / "audience").glob("*.md")
            ) if (brand_dir / "audience").exists() else False,
        }
        score = sum(25 for v in checks.values() if v)
        return {"score": score, "checks": checks}
