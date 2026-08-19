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
import logging
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.config.settings import PROJECT_ROOT
from src.utils.paths import (
    InvalidPathError,
    atomic_write_text,
    is_valid_id,
    safe_join,
    validate_id,
)

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge_base"
BRANDS_DIR = KNOWLEDGE_DIR / "brands"
GLOBAL_DIR = KNOWLEDGE_DIR / "_global"


class BrandExistsError(Exception):
    """Đã có dữ liệu ở thư mục brand này — route layer map thành HTTP 409."""


def real_content_length(text: str) -> int:
    """
    Độ dài phần nội dung THẬT của một markdown, bỏ khung và placeholder.

    create_brand() sinh file mẫu đầy placeholder kiểu "(Thêm brand identity
    tại đây)" — riêng phần khung đó đã dài hơn 50 ký tự, nên phép đo ngây thơ
    len(file) > 50 sẽ chấm brand rỗng hoàn toàn là đã hoàn thành một nửa.
    Điểm hoàn thiện mà nói dối thì tệ hơn là không có.

    Dùng chung cho file đã ghi lẫn nội dung mới đang là đề xuất.
    """
    real = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        body = line.lstrip("-*").strip()
        # "(Sứ mệnh)", "- (Giá trị 1)", "_(chưa có trong tài liệu)_"
        if body.startswith("(") and body.endswith(")"):
            continue
        if body.startswith("_(") and body.endswith(")_"):
            continue
        real.append(body)

    return len(" ".join(real))


def completeness_from_contents(contents: dict[str, str]) -> dict:
    """
    Tính điểm hoàn thiện từ nội dung, không cần đụng đĩa.

    contents: {"identity.md": "...", "products/san_pham.md": "...", ...}
    Dùng để xem trước brand sẽ đầy tới đâu TRƯỚC KHI tạo nó.
    """
    def has_real(path: str) -> bool:
        return real_content_length(contents.get(path, "")) > 50

    def has_any_in(prefix: str) -> bool:
        return any(
            path.startswith(prefix) and real_content_length(text) > 0
            for path, text in contents.items()
        )

    checks = {
        "identity": has_real("identity.md"),
        "tone": has_real("tone_of_voice.md"),
        "product": has_any_in("products/"),
        "audience": has_any_in("audience/"),
    }
    return {"score": sum(25 for v in checks.values() if v), "checks": checks}


class BrandManager:
    """Manages brand knowledge base operations."""

    def _brand_dir(self, brand_id: str) -> Path:
        """
        Resolve thư mục của brand, chặn path traversal.

        MỌI method nhận brand_id từ user PHẢI đi qua đây.
        """
        validate_id(brand_id, "brand_id")
        return safe_join(BRANDS_DIR, brand_id)

    def _doc_path(self, brand_id: str, doc_path: str) -> Path:
        """
        Resolve đường dẫn document trong brand, chặn path traversal.

        doc_path có thể chứa thư mục con ('products/foo.md') nhưng không
        được thoát ra khỏi thư mục brand.
        """
        brand_dir = self._brand_dir(brand_id)
        return safe_join(brand_dir, doc_path)

    def list_brands(self) -> list[dict]:
        """List all brands with metadata and document counts."""
        brands = []
        if not BRANDS_DIR.exists():
            return brands

        for brand_dir in sorted(BRANDS_DIR.iterdir()):
            # Bỏ qua thư mục có tên không hợp lệ (không thể truy cập qua API)
            if not is_valid_id(brand_dir.name):
                continue
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
        brand_dir = self._brand_dir(brand_id)
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
        """
        Create a new brand with default template files.

        Route đã kiểm brand tồn tại chưa bằng get_brand(), nhưng get_brand trả
        None khi thiếu brand.json — thư mục có sẵn mà thiếu file meta (tạo dở,
        hoặc ghi lỗi) sẽ lọt qua và bị ghi đè identity.md / tone_of_voice.md /
        voice_profile.json. Chặn ở đây, nơi biết chắc.
        """
        brand_dir = self._brand_dir(brand_id)
        if brand_dir.exists() and any(brand_dir.iterdir()):
            raise BrandExistsError(
                f"Thư mục brand '{brand_id}' đã tồn tại và không rỗng"
            )
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
        atomic_write_text(
            brand_dir / "identity.md",
            f"# {name}\n\n## Brand Identity\n\n(Thêm brand identity tại đây)\n\n"
            f"## Mission\n\n(Sứ mệnh)\n\n"
            f"## Unique Selling Proposition (USP)\n\n(Điều gì khiến brand khác biệt)\n\n"
            f"## Brand Values\n\n- (Giá trị 1)\n- (Giá trị 2)\n",
        )
        atomic_write_text(
            brand_dir / "tone_of_voice.md",
            f"# Tone of Voice — {name}\n\n## Overall Tone\n\n(Mô tả tone tại đây)\n\n"
            f"## Do's\n\n- (Nên viết kiểu gì)\n\n"
            f"## Don'ts\n\n- (Không viết kiểu gì)\n",
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
        atomic_write_text(
            brand_dir / "voice_profile.json",
            json.dumps(voice_profile, ensure_ascii=False, indent=2),
        )

        return meta

    def clone_brand(
        self,
        source_id: str,
        new_id: str,
        name: str,
        description: str = "",
        color: str = "#6c5ce7",
        icon: str = "📦",
        include_products: bool = False,
    ) -> dict:
        """
        Nhân bản một brand: giữ nhận diện, giọng, khung bài, khách hàng, quy
        định — nhưng MẶC ĐỊNH bỏ sản phẩm.

        Vì sao mặc định bỏ: người ta nhân bản chủ yếu để làm brand cùng ngành
        khác sản phẩm. Chép luôn sản phẩm cũ sang thì bài viết sẽ nói về hàng
        của brand khác, mà reviewer lại coi knowledge_base là nguồn sự thật
        nên sẽ không bắt được lỗi đó.

        KHÔNG chép _sources/: tài liệu gốc thuộc về brand cũ.
        """
        source_dir = self._brand_dir(source_id)
        if not source_dir.exists():
            raise FileNotFoundError(f"Brand nguồn '{source_id}' không tồn tại")

        target_dir = self._brand_dir(new_id)
        if target_dir.exists() and any(target_dir.iterdir()):
            raise BrandExistsError(f"Thư mục brand '{new_id}' đã tồn tại và không rỗng")

        bo_qua = {"_sources"} | (set() if include_products else {"products"})

        for src in source_dir.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(source_dir)
            if rel.parts and rel.parts[0] in bo_qua:
                continue
            if rel.name == "brand.json":
                continue  # dựng lại bên dưới, không chép nguyên

            dest = target_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

        # Thư mục rỗng vẫn phải có để UI thêm tài liệu vào được
        for sub in ("products", "audience"):
            (target_dir / sub).mkdir(parents=True, exist_ok=True)

        source_meta = self._load_brand_meta(source_id) or {}
        meta = {
            "id": new_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "color": color,
            "icon": icon,
            # Những ràng buộc này thường theo ngành nên chép sang là đúng
            "default_channels": source_meta.get("default_channels", ["facebook", "instagram"]),
            "default_goal": source_meta.get("default_goal", "awareness"),
            "forbidden_claims": list(source_meta.get("forbidden_claims", [])),
            "mandatory_terms": list(source_meta.get("mandatory_terms", [])),
            "cloned_from": source_id,
        }
        self._save_brand_meta(new_id, meta)

        # voice_profile.json mang profile_id của brand cũ, phải đổi
        voice_path = target_dir / "voice_profile.json"
        if voice_path.exists():
            try:
                profile = json.loads(voice_path.read_text(encoding="utf-8"))
                profile["profile_id"] = new_id
                atomic_write_text(
                    voice_path, json.dumps(profile, ensure_ascii=False, indent=2)
                )
            except (OSError, ValueError) as e:
                logger.warning("Không sửa được profile_id khi nhân bản: %s", e)

        return meta

    def delete_brand(self, brand_id: str) -> bool:
        """Delete a brand and all its knowledge."""
        brand_dir = self._brand_dir(brand_id)
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
        file_path = self._doc_path(brand_id, doc_path)
        if file_path.exists() and file_path.suffix == ".md":
            return file_path.read_text(encoding="utf-8")
        return None

    def doc_target(self, brand_id: str, doc_path: str) -> Path:
        """
        Đường dẫn thật của một document, đã qua kiểm an toàn.

        Dùng khi cần GOM nhiều file rồi ghi một lượt (xem apply_draft) thay vì
        ghi lần lượt từng cái.
        """
        if not doc_path.endswith(".md"):
            doc_path += ".md"
        return self._doc_path(brand_id, doc_path)

    def touch_brand(self, brand_id: str) -> None:
        """Cập nhật updated_at sau khi nội dung brand thay đổi."""
        meta = self._load_brand_meta(brand_id)
        if meta:
            meta["updated_at"] = datetime.now().isoformat()
            self._save_brand_meta(brand_id, meta)

    def save_document(self, brand_id: str, doc_path: str, content: str) -> bool:
        """Create or update a document."""
        if not doc_path.endswith(".md"):
            doc_path += ".md"

        file_path = self._doc_path(brand_id, doc_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(file_path, content)

        # Update brand modified time
        meta = self._load_brand_meta(brand_id)
        if meta:
            meta["updated_at"] = datetime.now().isoformat()
            self._save_brand_meta(brand_id, meta)

        return True

    def delete_document(self, brand_id: str, doc_path: str) -> bool:
        """Delete a document. Chỉ xóa được file .md trong thư mục brand."""
        file_path = self._doc_path(brand_id, doc_path)
        if file_path.is_file() and file_path.suffix == ".md":
            file_path.unlink()
            return True
        return False

    # === Tài liệu gốc người dùng đã nạp ===

    def save_source(self, brand_id: str, name: str, text: str) -> str:
        """
        Lưu nguyên văn tài liệu người dùng dán vào, để sau này đọc lại được
        bằng prompt tốt hơn mà không phải đi tìm lại bài cũ.

        Ghi dưới dạng .txt trong _sources/ nên:
          - retriever KHÔNG nạp (nó chỉ đọc tên file cố định + products/,
            audience/, policies/ dạng .md)
          - get_brand() không liệt kê ra tab Tài liệu (rglob "*.md")
        Tức là tài liệu gốc không lẫn vào knowledge, chỉ nằm đó để tra lại.
        """
        validate_id(name, "source_name")
        base_dir = safe_join(self._brand_dir(brand_id), "_sources")
        base_dir.mkdir(parents=True, exist_ok=True)

        # Nạp liệu nhiều lần thì tên sẽ đụng nhau. Trùng tên mà TRÙNG luôn nội
        # dung thì bỏ qua (nạp lại đúng bài cũ, không cần bản sao); khác nội
        # dung thì đánh số để không đè mất tài liệu lần trước.
        path = base_dir / f"{name}.txt"
        stt = 1
        while path.exists():
            if path.read_text(encoding="utf-8") == text:
                return f"_sources/{path.name}"
            stt += 1
            path = base_dir / f"{name}_{stt}.txt"

        atomic_write_text(path, text)
        return f"_sources/{path.name}"

    def list_sources(self, brand_id: str) -> list[str]:
        sources_dir = self._brand_dir(brand_id) / "_sources"
        if not sources_dir.exists():
            return []
        return sorted(f.name for f in sources_dir.glob("*.txt"))

    # === Voice Profile ===

    def get_voice_profile(self, brand_id: str) -> Optional[dict]:
        """Get voice profile for a brand."""
        file_path = self._brand_dir(brand_id) / "voice_profile.json"
        if file_path.exists():
            return json.loads(file_path.read_text(encoding="utf-8"))
        return None

    def update_voice_profile(self, brand_id: str, profile: dict) -> bool:
        """Update voice profile for a brand."""
        file_path = self._brand_dir(brand_id) / "voice_profile.json"
        if not file_path.parent.exists():
            return False
        atomic_write_text(file_path, json.dumps(profile, ensure_ascii=False, indent=2))
        return True

    # === Knowledge Preview ===

    def get_knowledge_preview(self, brand_id: str) -> Optional[dict]:
        """Get full knowledge preview with token estimate."""
        brand_dir = self._brand_dir(brand_id)
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
            # Claude context window thật là 200k, không phải 150k
            "context_usage_percent": round(estimated_tokens / 200_000 * 100, 1),
        }

    # === Internal helpers ===

    def _load_brand_meta(self, brand_id: str) -> Optional[dict]:
        meta_path = self._brand_dir(brand_id) / "brand.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text(encoding="utf-8"))
        return None

    def _save_brand_meta(self, brand_id: str, meta: dict):
        meta_path = self._brand_dir(brand_id) / "brand.json"
        atomic_write_text(meta_path, json.dumps(meta, ensure_ascii=False, indent=2))

    def _categorize_doc(self, rel_path: Path) -> str:
        """Categorize a document by its relative path."""
        parts = rel_path.parts
        if len(parts) > 1:
            return parts[0]  # "products", "audience", "policies"
        stem = rel_path.stem
        if stem in ("identity", "tone_of_voice", "visual_guidelines"):
            return "brand_core"
        return "general"

    @staticmethod
    def _real_content_length(path: Path) -> int:
        """Bản đọc-từ-đĩa của real_content_length()."""
        if not path.exists():
            return 0
        return real_content_length(path.read_text(encoding="utf-8"))

    def _calc_completeness(self, brand_dir: Path) -> dict:
        """Calculate knowledge completeness (4 dimensions × 25%)."""
        checks = {
            "identity": self._real_content_length(brand_dir / "identity.md") > 50,
            "tone": self._real_content_length(brand_dir / "tone_of_voice.md") > 50,
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
