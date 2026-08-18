"""
Brand Management API routes.

CRUD operations for brands, documents, and voice profiles.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from src.knowledge import brand_bootstrap
from src.knowledge.brand_manager import BrandExistsError, BrandManager
from src.utils.paths import validate_id

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


class BootstrapVoiceRequest(BaseModel):
    """Chặng 1 — những bài brand đã từng đăng."""
    samples: list[str] = Field(min_length=1)


class BootstrapBrandRequest(BaseModel):
    """Chặng 2 — tài liệu về brand và khách hàng."""
    documents: list[str] = Field(min_length=1)


class CreationPreviewRequest(BaseModel):
    """
    Tài liệu để dựng một brand CHƯA TỒN TẠI.

    Hai loại tài liệu đều không bắt buộc, nhưng phải có ít nhất một —
    kiểm ở tầng route để báo lỗi rõ hơn là để Pydantic báo chung chung.
    """
    samples: list[str] = Field(default_factory=list)     # bài đã đăng
    documents: list[str] = Field(default_factory=list)   # tài liệu brand
    name_hint: str = ""                                  # người dùng gõ sẵn tên


class CreateFromDraftRequest(BaseModel):
    """Tạo brand thật, sau khi người dùng đã duyệt bản đề xuất."""
    id: str
    name: str
    description: str = ""
    color: str = "#6c5ce7"
    icon: str = "📦"
    files: list[brand_bootstrap.FileDraft] = Field(default_factory=list)
    voice_profile: Optional[dict] = None
    brand_meta: Optional[dict] = None
    # Nguyên văn tài liệu đã dán, lưu lại để sau đọc lại được bằng prompt tốt
    # hơn mà không phải đi tìm bài cũ. Không bắt buộc.
    sources: dict[str, str] = Field(default_factory=dict)


class ApplyDraftRequest(BaseModel):
    """
    Chỉ những gì người dùng đã duyệt. UI bỏ chọn file nào thì file đó không có
    trong danh sách này — server không tự suy diễn thêm.
    """
    files: list[brand_bootstrap.FileDraft] = Field(default_factory=list)
    voice_profile: Optional[dict] = None
    brand_meta: Optional[dict] = None


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
    try:
        return manager.create_brand(req.id, req.name, req.description, req.color, req.icon)
    except BrandExistsError as e:
        # Thư mục đã có dữ liệu nhưng thiếu brand.json — không ghi đè
        raise HTTPException(status_code=409, detail=str(e)) from e


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


# === Bootstrap knowledge base ===
#
# Hai chặng nạp liệu, tích luỹ dần. Cả hai chỉ TRẢ VỀ DRAFT — người dùng đối
# chiếu với nội dung đang có rồi mới bấm apply. Xem src/knowledge/brand_bootstrap.py
# để biết vì sao bước duyệt là bắt buộc chứ không phải cho đẹp.


def _require_brand(brand_id: str) -> dict:
    brand = manager.get_brand(brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


def _guard_size(chunks: list[str]) -> None:
    try:
        brand_bootstrap.check_input_size(chunks)
    except ValueError as e:
        raise HTTPException(status_code=413, detail={"message": str(e)}) from e


@router.post("/{brand_id}/bootstrap/voice", response_model=brand_bootstrap.BootstrapDraft)
def bootstrap_voice(brand_id: str, req: BootstrapVoiceRequest):
    """Chặng 1: đọc bài đã đăng, rút giọng văn và khung bài."""
    brand = _require_brand(brand_id)
    _guard_size(req.samples)

    voice = brand_bootstrap.extract_voice(req.samples)
    return brand_bootstrap.build_voice_draft(
        manager, brand_id, brand.get("name", brand_id), voice
    )


@router.post("/{brand_id}/bootstrap/brand", response_model=brand_bootstrap.BootstrapDraft)
def bootstrap_brand(brand_id: str, req: BootstrapBrandRequest):
    """Chặng 2: đọc tài liệu về brand và khách hàng, rút bộ khung brand."""
    brand = _require_brand(brand_id)
    _guard_size(req.documents)

    extracted = brand_bootstrap.extract_brand(req.documents)
    return brand_bootstrap.build_brand_draft(
        manager, brand_id, brand.get("name", brand_id), extracted
    )


@router.post("/{brand_id}/bootstrap/apply")
def bootstrap_apply(brand_id: str, req: ApplyDraftRequest):
    """Ghi phần người dùng đã duyệt. Không duyệt thì không ghi."""
    _require_brand(brand_id)

    if not req.files and not req.voice_profile and not req.brand_meta:
        raise HTTPException(
            status_code=400, detail={"message": "Chưa chọn gì để lưu."}
        )

    return brand_bootstrap.apply_draft(
        manager,
        brand_id,
        req.files,
        voice_profile=req.voice_profile,
        brand_meta=req.brand_meta,
    )


# === Tạo brand TỪ tài liệu ===
#
# Khác với /bootstrap/{voice,brand} ở trên (chạy trên brand đã có để bổ sung),
# hai endpoint này chạy khi CHƯA có brand: đọc tài liệu trước, đề xuất cả tên
# lẫn mã brand, rồi mới tạo. Tài liệu là điểm xuất phát.


@router.post("/bootstrap/preview", response_model=brand_bootstrap.CreationPreview)
def bootstrap_preview(req: CreationPreviewRequest):
    """
    Đọc tài liệu và dựng đề xuất cho một brand chưa tồn tại.

    KHÔNG tạo gì cả. Trả về tên/mã đề xuất, các file sẽ ghi, và điểm hoàn
    thiện dự kiến để người dùng biết brand sẽ bắt đầu ở mức nào.
    """
    if not any(c.strip() for c in req.samples + req.documents):
        raise HTTPException(
            status_code=400,
            detail={"message": "Cần ít nhất một bài đã đăng hoặc một tài liệu về brand."},
        )
    _guard_size(req.samples + req.documents)

    try:
        voice, brand = brand_bootstrap.extract_for_creation(req.samples, req.documents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e)}) from e

    return brand_bootstrap.build_creation_preview(manager, voice, brand, req.name_hint)


@router.post("/bootstrap/create")
def bootstrap_create(req: CreateFromDraftRequest):
    """Tạo brand thật từ bản đề xuất người dùng đã duyệt và chỉnh."""
    validate_id(req.id, "brand_id")

    if manager.get_brand(req.id):
        raise HTTPException(status_code=409, detail="Brand already exists")
    if not req.name.strip():
        raise HTTPException(status_code=400, detail={"message": "Brand cần có tên."})

    try:
        return brand_bootstrap.create_brand_from_draft(
            manager,
            req.id,
            req.name.strip(),
            req.description.strip(),
            req.files,
            voice_profile=req.voice_profile,
            brand_meta=req.brand_meta,
            sources=req.sources,
            icon=req.icon,
            color=req.color,
        )
    except BrandExistsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
