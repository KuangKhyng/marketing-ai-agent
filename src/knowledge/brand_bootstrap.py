"""
Bootstrap knowledge base của một brand từ tài liệu người dùng đưa vào.

Vấn đề nó giải: brand mới tạo xong chỉ có file markdown rỗng kèm placeholder
"(Thêm brand identity tại đây)". Người dùng đối diện màn hình trắng và phải
đoán xem viết gì, viết bao nhiêu, viết thế nào thì pipeline dùng được.

Hai chặng, nạp dần:

    Chặng 1 — bài đã viết   -> khung viết chung
              extract_voice()  voice_profile.json, tone_of_voice.md,
                               content_framework.md

    Chặng 2 — docs về brand -> bộ khung brand chuẩn
              extract_brand()  identity.md, products/*.md, audience/*.md,
                               gợi ý forbidden_claims / mandatory_terms

NGUYÊN TẮC: cả hai chặng chỉ trả về DRAFT, không ghi file. Người dùng đối
chiếu với nội dung đang có rồi mới quyết định ghi (`apply_draft`).

Vì sao bắt buộc phải qua người: knowledge_base là ground truth của pipeline —
reviewer chấm `factuality` dựa vào nó, và brief_parser cố tình ghi đè brand từ
UI để LLM không tự bịa (xem `_override_brand_from_state`). Để LLM tự suy ra
"USP của brand" rồi ghi thẳng vào ground truth là phá đúng nguyên tắc đó.
"""
import logging
from typing import Optional

from pydantic import BaseModel, Field

from src.knowledge.brand_manager import BrandManager
from src.utils.paths import InvalidPathError

logger = logging.getLogger(__name__)

# Giới hạn tổng độ dài input. Chặn cả chi phí lẫn việc nhồi quá context.
MAX_INPUT_CHARS = 60_000

# Retriever chỉ nạp tối đa 2 file product và 1 file audience
# (src/knowledge/retriever.py::_smart_load_dir), chọn bằng keyword scoring chỉ
# quét 500 ký tự đầu. Sinh nhiều hơn thì file thừa bị bỏ âm thầm — nên gom ít
# file mà đầy đủ, đừng rải mỗi sản phẩm một file.
MAX_PRODUCT_FILES = 2
MAX_AUDIENCE_FILES = 1


# === Schema LLM trả về ===


class VoiceExtraction(BaseModel):
    """Chặng 1 — rút giọng văn và khung bài từ những bài đã viết."""

    tone_primary: str = Field(description="Tone chủ đạo, một hai từ (vd: thân mật, chuyên nghiệp)")
    tone_secondary: str = Field(default="", description="Tone phụ")
    formality: float = Field(ge=0, le=1, description="0 = rất suồng sã, 1 = rất trang trọng")
    perspective: str = Field(
        default="second_person",
        description="first_person | second_person | third_person — cách xưng hô hay dùng",
    )
    avg_sentence_length: int = Field(default=15, description="Độ dài câu trung bình, tính bằng từ")

    preferred_words: list[str] = Field(
        default_factory=list, description="Từ/cụm brand hay dùng, lấy nguyên văn từ bài mẫu"
    )
    avoided_words: list[str] = Field(
        default_factory=list, description="Từ brand rõ ràng né, suy ra từ việc chúng không xuất hiện"
    )
    emoji_style: str = Field(default="moderate", description="none | light | moderate | heavy")
    common_emojis: list[str] = Field(default_factory=list)

    anti_ai_rules: list[str] = Field(
        default_factory=list,
        description="Lối viết cần tránh để không ra giọng AI, suy từ đặc điểm bài mẫu",
    )

    tone_summary: str = Field(description="Mô tả tổng thể giọng brand, 2-4 câu")
    dos: list[str] = Field(default_factory=list, description="Nên viết thế nào")
    donts: list[str] = Field(default_factory=list, description="Không nên viết thế nào")

    # Khung bài — cấu trúc, khác với giọng
    hook_patterns: list[str] = Field(
        default_factory=list, description="Các kiểu mở bài brand hay dùng, mô tả rồi cho ví dụ thật"
    )
    body_structure: str = Field(default="", description="Thân bài thường triển khai theo trình tự nào")
    cta_style: str = Field(default="", description="Cách kêu gọi hành động đặc trưng")
    framework_notes: str = Field(default="", description="Quy ước khác: độ dài, xuống dòng, hashtag")


class ProductDraft(BaseModel):
    name: str
    summary: str = Field(description="Một câu mô tả")
    details: str = Field(default="", description="Đặc điểm, lợi ích, giá nếu tài liệu có nói")


class AudienceDraft(BaseModel):
    persona_name: str = Field(default="Khách hàng chính")
    description: str
    age_range: str = ""
    pain_points: list[str] = Field(default_factory=list)
    motivations: list[str] = Field(default_factory=list)


class BrandExtraction(BaseModel):
    """Chặng 2 — rút bộ khung brand từ tài liệu."""

    identity: str = Field(description="Brand là ai, làm gì. 2-5 câu.")
    mission: str = Field(default="", description="Sứ mệnh, nếu tài liệu có nói")
    usp: str = Field(default="", description="Điều khiến khách chọn brand này thay vì đối thủ")
    values: list[str] = Field(default_factory=list)

    products: list[ProductDraft] = Field(default_factory=list)
    audience: Optional[AudienceDraft] = None

    forbidden_claims: list[str] = Field(
        default_factory=list,
        description="Điều tuyệt đối không được khẳng định (cam kết chữa khỏi, số liệu chưa kiểm chứng...)",
    )
    mandatory_terms: list[str] = Field(
        default_factory=list, description="Từ/cụm bắt buộc phải có trong mọi bài"
    )

    uncertain: list[str] = Field(
        default_factory=list,
        description="Điều KHÔNG suy được chắc chắn từ tài liệu — nêu ra để người dùng tự điền, "
                    "TUYỆT ĐỐI không bịa",
    )


# === Draft trả về cho UI ===


class FileDraft(BaseModel):
    """Một file đề xuất ghi, kèm nội dung hiện tại để UI đối chiếu."""

    path: str
    content: str
    exists: bool = False
    current: Optional[str] = None
    label: str = ""


class BootstrapDraft(BaseModel):
    files: list[FileDraft] = Field(default_factory=list)
    voice_profile: Optional[dict] = None
    brand_meta: dict = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


# === Dựng markdown từ kết quả extract ===


def _bullets(items: list[str], empty: str = "_(chưa có)_") -> str:
    return "\n".join(f"- {i}" for i in items) if items else empty


def render_tone_of_voice(voice: VoiceExtraction, brand_name: str) -> str:
    return f"""# Tone of Voice — {brand_name}

## Overall Tone

{voice.tone_summary}

Tone chủ đạo: **{voice.tone_primary}**{f" · phụ: {voice.tone_secondary}" if voice.tone_secondary else ""}
Mức trang trọng: {voice.formality:.1f}/1.0 · Xưng hô: {voice.perspective}
Câu trung bình khoảng {voice.avg_sentence_length} từ

## Do's

{_bullets(voice.dos)}

## Don'ts

{_bullets(voice.donts)}
"""


def render_content_framework(voice: VoiceExtraction, brand_name: str) -> str:
    return f"""# Khung bài — {brand_name}

Rút từ những bài brand đã đăng. Đây là CẤU TRÚC bài, khác với giọng văn
(xem `tone_of_voice.md`).

## Cách mở bài

{_bullets(voice.hook_patterns)}

## Triển khai thân bài

{voice.body_structure or "_(chưa rút được từ bài mẫu)_"}

## Kêu gọi hành động

{voice.cta_style or "_(chưa rút được từ bài mẫu)_"}

## Quy ước khác

{voice.framework_notes or "_(chưa có)_"}
"""


def render_identity(brand: BrandExtraction, brand_name: str) -> str:
    return f"""# {brand_name}

## Brand Identity

{brand.identity}

## Mission

{brand.mission or "_(chưa có trong tài liệu)_"}

## Unique Selling Proposition (USP)

{brand.usp or "_(chưa có trong tài liệu)_"}

## Brand Values

{_bullets(brand.values)}
"""


def render_products(products: list[ProductDraft]) -> str:
    """
    Gom TẤT CẢ sản phẩm vào một file.

    Retriever chỉ nạp tối đa 2 file trong products/, nên tách mỗi sản phẩm một
    file là cách chắc chắn để mất sản phẩm thứ ba trở đi.
    """
    parts = ["# Sản phẩm & dịch vụ", ""]
    for p in products:
        parts.append(f"## {p.name}")
        parts.append("")
        parts.append(p.summary)
        if p.details:
            parts.append("")
            parts.append(p.details)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def render_audience(audience: AudienceDraft) -> str:
    return f"""# {audience.persona_name}

{audience.description}

**Độ tuổi:** {audience.age_range or "_(chưa rõ)_"}

## Trăn trở

{_bullets(audience.pain_points)}

## Điều họ muốn

{_bullets(audience.motivations)}
"""


def build_voice_profile(voice: VoiceExtraction, brand_id: str) -> dict:
    """Khớp đúng schema voice_profile.json mà retriever và các node đang đọc."""
    return {
        "profile_id": brand_id,
        "tone": {
            "primary": voice.tone_primary,
            "secondary": voice.tone_secondary,
            "formality": round(voice.formality, 2),
        },
        "writing_style": {
            "avg_sentence_length": voice.avg_sentence_length,
            "perspective": voice.perspective,
        },
        "vocabulary": {
            "preferred": voice.preferred_words,
            "avoided": voice.avoided_words,
            "emoji_style": voice.emoji_style,
            "common_emojis": voice.common_emojis,
        },
        "anti_ai_rules": voice.anti_ai_rules,
    }


# === Ghép thành draft ===


def _attach_current(manager: BrandManager, brand_id: str, draft: FileDraft) -> FileDraft:
    """Gắn nội dung đang có của file để UI đối chiếu trước khi ghi đè."""
    try:
        current = manager.get_document(brand_id, draft.path)
    except InvalidPathError:
        current = None
    draft.exists = current is not None
    draft.current = current
    return draft


def build_voice_draft(
    manager: BrandManager, brand_id: str, brand_name: str, voice: VoiceExtraction
) -> BootstrapDraft:
    files = [
        FileDraft(
            path="tone_of_voice.md",
            label="Giọng văn",
            content=render_tone_of_voice(voice, brand_name),
        ),
        FileDraft(
            path="content_framework.md",
            label="Khung bài",
            content=render_content_framework(voice, brand_name),
        ),
    ]
    return BootstrapDraft(
        files=[_attach_current(manager, brand_id, f) for f in files],
        voice_profile=build_voice_profile(voice, brand_id),
        notes=[],
    )


def build_brand_draft(
    manager: BrandManager, brand_id: str, brand_name: str, brand: BrandExtraction
) -> BootstrapDraft:
    files = [
        FileDraft(
            path="identity.md",
            label="Nhận diện brand",
            content=render_identity(brand, brand_name),
        )
    ]

    if brand.products:
        files.append(
            FileDraft(
                path="products/san_pham.md",
                label="Sản phẩm & dịch vụ",
                content=render_products(brand.products),
            )
        )

    if brand.audience:
        files.append(
            FileDraft(
                path="audience/khach_hang_chinh.md",
                label="Khách hàng mục tiêu",
                content=render_audience(brand.audience),
            )
        )

    meta = {}
    if brand.forbidden_claims:
        meta["forbidden_claims"] = brand.forbidden_claims
    if brand.mandatory_terms:
        meta["mandatory_terms"] = brand.mandatory_terms

    notes = []
    if brand.uncertain:
        notes.append("Tài liệu chưa đủ để suy ra: " + "; ".join(brand.uncertain))

    return BootstrapDraft(
        files=[_attach_current(manager, brand_id, f) for f in files],
        brand_meta=meta,
        notes=notes,
    )


# === Ghi draft xuống ===


def apply_draft(
    manager: BrandManager,
    brand_id: str,
    files: list[FileDraft],
    voice_profile: Optional[dict] = None,
    brand_meta: Optional[dict] = None,
) -> dict:
    """
    Ghi những gì người dùng đã duyệt.

    Chỉ ghi đúng thứ được truyền vào — UI bỏ chọn file nào thì file đó không
    có trong danh sách. Mọi đường dẫn đi qua BrandManager nên vẫn được
    validate_id + safe_join chặn path traversal.
    """
    written = []
    for f in files:
        manager.save_document(brand_id, f.path, f.content)
        written.append(f.path)

    if voice_profile:
        manager.update_voice_profile(brand_id, voice_profile)
        written.append("voice_profile.json")

    if brand_meta:
        manager.update_brand_meta(brand_id, brand_meta)
        written.append("brand.json")

    logger.info("Bootstrap brand %s: ghi %s", brand_id, ", ".join(written))
    return {"written": written}


def check_input_size(chunks: list[str]) -> int:
    """
    Tổng độ dài input. Raise ValueError nếu vượt ngưỡng.

    Route layer map thành HTTP 413.
    """
    total = sum(len(c) for c in chunks)
    if total > MAX_INPUT_CHARS:
        raise ValueError(
            f"Tài liệu quá dài ({total:,} ký tự, tối đa {MAX_INPUT_CHARS:,}). "
            "Bớt bớt hoặc chia làm nhiều lần nạp."
        )
    return total


# === Gọi LLM ===
#
# Tách riêng khỏi phần dựng markdown ở trên để test được toàn bộ logic render
# và merge mà không cần API. Chỉ hai hàm dưới đây chạm mạng.

from pathlib import Path  # noqa: E402

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "v1"


def _build_llm():
    """Dựng LLM theo config node brand_bootstrap. Import trong hàm cho nhẹ."""
    from langchain_anthropic import ChatAnthropic

    from src.config.settings import get_api_key, get_model_config

    config = get_model_config("brand_bootstrap")
    if not config:
        raise ValueError("Thiếu cấu hình model cho node brand_bootstrap trong models.yaml")

    return ChatAnthropic(
        model=config["model"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
        api_key=get_api_key(),
    )


def _invoke(prompt_file: str, schema, header: str, chunks: list[str]):
    from langchain_core.messages import HumanMessage, SystemMessage

    system_prompt = (PROMPTS_DIR / prompt_file).read_text(encoding="utf-8")

    numbered = "\n\n---\n\n".join(
        f"### {header} {i}\n\n{chunk.strip()}" for i, chunk in enumerate(chunks, 1) if chunk.strip()
    )
    if not numbered:
        raise ValueError("Chưa có nội dung nào để đọc.")

    structured = _build_llm().with_structured_output(schema)
    return structured.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=numbered),
    ])


def extract_voice(samples: list[str]) -> VoiceExtraction:
    """Chặng 1: bài đã đăng -> giọng văn + khung bài."""
    check_input_size(samples)
    logger.info("Bootstrap giọng: đọc %d bài mẫu", len(samples))
    return _invoke("brand_bootstrap_voice.md", VoiceExtraction, "Bài", samples)


def extract_brand(documents: list[str]) -> BrandExtraction:
    """Chặng 2: tài liệu về brand -> bộ khung brand."""
    check_input_size(documents)
    logger.info("Bootstrap brand: đọc %d tài liệu", len(documents))
    return _invoke("brand_bootstrap_brand.md", BrandExtraction, "Tài liệu", documents)
