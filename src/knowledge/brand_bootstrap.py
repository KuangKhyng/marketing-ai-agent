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
import hashlib
import logging
from datetime import datetime, timedelta
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

    # Hai trường này chỉ dùng khi TẠO brand từ tài liệu. Nạp liệu cho brand đã
    # có thì bỏ qua, không ghi đè tên người dùng đã đặt.
    brand_name: str = Field(
        default="",
        description="Tên brand đúng như tài liệu gọi. Không có thì để rỗng, đừng tự đặt.",
    )
    short_description: str = Field(
        default="",
        description="Một câu: brand làm gì, ở đâu. Ví dụ 'Quán cà phê specialty tại quận 1'.",
    )

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
    # Lần đọc này tốn bao nhiêu. cached=True nghĩa là không tốn gì.
    usage: Optional["ExtractUsage"] = None


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


def _save_sources(manager: BrandManager, brand_id: str, sources: Optional[dict]) -> list[str]:
    """
    Giữ nguyên văn tài liệu người dùng đã dán.

    Lỗi ở đây không được kéo theo cả thao tác: đây là tiện ích để sau đọc lại,
    không phải phần bắt buộc của việc ghi knowledge.
    """
    written = []
    for name, text in (sources or {}).items():
        try:
            written.append(manager.save_source(brand_id, name, text))
        except Exception as e:
            logger.warning("Không lưu được tài liệu gốc %s: %s", name, e)
    return written


def apply_draft(
    manager: BrandManager,
    brand_id: str,
    files: list[FileDraft],
    voice_profile: Optional[dict] = None,
    brand_meta: Optional[dict] = None,
    sources: Optional[dict[str, str]] = None,
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

    written.extend(_save_sources(manager, brand_id, sources))

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


# === Chi phí: ước tính trước, cache, và đo thật ===
#
# Mỗi lần bấm đọc là một lượt gọi Sonnet có tính tiền. Một dòng chữ cảnh báo
# không đủ — người ta vẫn sẽ sửa vài chữ rồi bấm lại chục lần. Nên:
#   1. estimate_cost_for() cho biết trước sẽ tốn bao nhiêu
#   2. cache theo nội dung: đọc lại đúng tài liệu cũ thì KHÔNG gọi API
#   3. mọi lần đọc đều trả về usage thật để hiện lên UI

_EXTRACT_CACHE_DIR = None  # tính lười, xem _cache_dir()
_EXTRACT_CACHE_TTL_HOURS = 24


def _cache_dir() -> Path:
    from src.config.settings import PROJECT_ROOT

    return PROJECT_ROOT / "outputs" / "cache" / "bootstrap"


class ExtractUsage(BaseModel):
    """Chi phí của một lượt đọc. cached=True nghĩa là không tốn gì."""

    input_tokens: int = 0
    output_tokens: int = 0
    cost_estimate: float = 0.0
    cached: bool = False

    def add(self, other: "ExtractUsage") -> "ExtractUsage":
        return ExtractUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cost_estimate=round(self.cost_estimate + other.cost_estimate, 6),
            cached=self.cached and other.cached,
        )


class CostEstimate(BaseModel):
    """Dự báo trước khi gọi. Không chạm mạng."""

    input_chars: int = 0
    estimated_input_tokens: int = 0
    estimated_cost: float = 0.0
    model: str = ""
    cached: bool = False   # đã có sẵn kết quả cho đúng tài liệu này chưa


def _model_name() -> str:
    from src.config.settings import get_model_config

    return (get_model_config("brand_bootstrap") or {}).get("model", "")


def _prompt_text(prompt_file: str) -> str:
    return (PROMPTS_DIR / prompt_file).read_text(encoding="utf-8")


def _cache_key(prompt_file: str, chunks: list[str]) -> str:
    """
    Khoá gồm cả PROMPT: sửa prompt là kết quả cũ hết giá trị, phải đọc lại.
    """
    h = hashlib.sha256()
    h.update(_prompt_text(prompt_file).encode("utf-8"))
    h.update(_model_name().encode("utf-8"))
    for c in chunks:
        h.update(b"\x1f")
        h.update(c.strip().encode("utf-8"))
    return h.hexdigest()[:20]


def _cache_read(key: str, schema):
    path = _cache_dir() / f"{key}.json"
    if not path.exists():
        return None
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    if age > timedelta(hours=_EXTRACT_CACHE_TTL_HOURS):
        path.unlink(missing_ok=True)
        return None
    try:
        return schema.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.info("Bỏ cache bootstrap không đọc được %s: %s", path.name, e)
        path.unlink(missing_ok=True)
        return None


def _cache_write(key: str, value) -> None:
    try:
        d = _cache_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{key}.json").write_text(value.model_dump_json(indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning("Không ghi được cache bootstrap: %s", e)


def has_cached(prompt_file: str, chunks: list[str], schema) -> bool:
    chunks = [c for c in chunks if c.strip()]
    if not chunks:
        return False
    return _cache_read(_cache_key(prompt_file, chunks), schema) is not None


def estimate_cost_for(samples: list[str], documents: list[str]) -> CostEstimate:
    """
    Ước tính trước khi gọi. KHÔNG chạm mạng, không tốn gì.

    Dùng chính estimate_tokens() và bảng giá của pipeline nên con số hiện ra
    cùng đơn vị với chi phí campaign — một nguồn giá duy nhất.
    """
    from src.config.settings import estimate_cost
    from src.utils.callbacks import estimate_tokens

    samples = [c for c in samples if c.strip()]
    documents = [c for c in documents if c.strip()]

    model = _model_name()
    total_tokens = 0
    all_cached = bool(samples or documents)

    for chunks, prompt_file, schema in (
        (samples, "brand_bootstrap_voice.md", VoiceExtraction),
        (documents, "brand_bootstrap_brand.md", BrandExtraction),
    ):
        if not chunks:
            continue
        total_tokens += estimate_tokens(_prompt_text(prompt_file) + "".join(chunks))
        if not has_cached(prompt_file, chunks, schema):
            all_cached = False

    # Output khó đoán; lấy 1500 token/lượt làm mức thường thấy của schema này
    luot = bool(samples) + bool(documents)
    output_tokens = 1500 * luot

    return CostEstimate(
        input_chars=sum(len(c) for c in samples + documents),
        estimated_input_tokens=total_tokens,
        estimated_cost=0.0 if all_cached else estimate_cost(model, total_tokens, output_tokens),
        model=model,
        cached=all_cached,
    )


def _invoke(prompt_file: str, schema, header: str, chunks: list[str]) -> tuple:
    """Trả về (kết quả, usage). Đọc cache trước, chỉ gọi API khi thật sự cần."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from src.config.settings import estimate_cost
    from src.utils.callbacks import TokenUsageHandler, estimate_tokens

    chunks = [c for c in chunks if c.strip()]
    if not chunks:
        raise ValueError("Chưa có nội dung nào để đọc.")

    # 1. Đúng tài liệu này, đúng prompt này thì đã đọc rồi — không trả tiền lần nữa
    key = _cache_key(prompt_file, chunks)
    cached = _cache_read(key, schema)
    if cached is not None:
        logger.info("Bootstrap %s: lấy từ cache, không gọi API", prompt_file)
        return cached, ExtractUsage(cached=True)

    system_prompt = _prompt_text(prompt_file)
    numbered = "\n\n---\n\n".join(
        f"### {header} {i}\n\n{chunk.strip()}" for i, chunk in enumerate(chunks, 1)
    )

    handler = TokenUsageHandler()
    structured = _build_llm().with_structured_output(schema)
    result = structured.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=numbered)],
        config={"callbacks": [handler]},
    )

    if handler.has_data:
        usage = handler.get_usage()
        input_tokens, output_tokens = usage["input"], usage["output"]
    else:
        input_tokens = estimate_tokens(system_prompt + numbered)
        output_tokens = estimate_tokens(result.model_dump_json())

    cost = estimate_cost(_model_name(), input_tokens, output_tokens)
    logger.info(
        "Bootstrap %s: %d vào / %d ra, ~$%.4f", prompt_file, input_tokens, output_tokens, cost
    )

    _cache_write(key, result)
    return result, ExtractUsage(
        input_tokens=input_tokens, output_tokens=output_tokens, cost_estimate=cost
    )


def extract_voice(samples: list[str]) -> tuple[VoiceExtraction, ExtractUsage]:
    """Chặng 1: bài đã đăng -> giọng văn + khung bài."""
    check_input_size(samples)
    return _invoke("brand_bootstrap_voice.md", VoiceExtraction, "Bài", samples)


def extract_brand(documents: list[str]) -> tuple[BrandExtraction, ExtractUsage]:
    """Chặng 2: tài liệu về brand -> bộ khung brand."""
    check_input_size(documents)
    return _invoke("brand_bootstrap_brand.md", BrandExtraction, "Tài liệu", documents)


# ============================================================
# Tạo brand TỪ tài liệu
#
# Khác với hai chặng ở trên (chạy trên brand đã tồn tại để bổ sung), phần này
# chạy khi CHƯA có brand nào: đọc tài liệu trước, đề xuất luôn cả tên và mã
# brand, rồi mới tạo. Tài liệu là điểm xuất phát, không phải thứ nhét vào sau.
# ============================================================

import unicodedata  # noqa: E402

# đ/Đ là chữ cái riêng trong bảng chữ cái tiếng Việt, NFD không tách được
_DAC_BIET = {"đ": "d", "Đ": "D"}


def slugify_brand_id(name: str, fallback: str = "brand_moi") -> str:
    """
    Đề xuất mã brand từ tên: "Tử Vi Online" -> "tu_vi_online".

    Mã này là TÊN THƯ MỤC và không đổi được sau khi tạo, nên đây chỉ là đề
    xuất — UI phải cho sửa. Kết quả luôn khớp _ID_RE trong src/utils/paths.py
    ([A-Za-z0-9_-], tối đa 64).
    """
    text = "".join(_DAC_BIET.get(ch, ch) for ch in (name or ""))
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))

    out = []
    for ch in text.lower():
        if ch.isascii() and (ch.isalnum() or ch in "_-"):
            out.append(ch)
        elif out and out[-1] != "_":
            out.append("_")

    slug = "".join(out).strip("_-")[:64].rstrip("_-")
    return slug or fallback


class BrandIdentityProposal(BaseModel):
    """Danh tính brand suy từ tài liệu. Mọi trường đều sửa được ở UI."""

    name: str = ""
    suggested_id: str = ""
    description: str = ""
    id_taken: bool = False


class CreationPreview(BaseModel):
    """Toàn bộ những gì sẽ được tạo, trước khi tạo bất cứ thứ gì."""

    identity: BrandIdentityProposal
    draft: BootstrapDraft
    completeness: dict = Field(default_factory=dict)


def _merge_drafts(*drafts: BootstrapDraft) -> BootstrapDraft:
    """Gộp kết quả hai chặng. Trùng path thì bản sau thắng."""
    files: dict[str, FileDraft] = {}
    voice_profile = None
    meta: dict = {}
    notes: list[str] = []

    for d in drafts:
        if d is None:
            continue
        for f in d.files:
            files[f.path] = f
        if d.voice_profile:
            voice_profile = d.voice_profile
        meta.update(d.brand_meta or {})
        notes.extend(d.notes or [])

    usage = None
    for d in drafts:
        if d is None or d.usage is None:
            continue
        usage = d.usage if usage is None else usage.add(d.usage)

    return BootstrapDraft(
        files=list(files.values()),
        voice_profile=voice_profile,
        brand_meta=meta,
        notes=notes,
        usage=usage,
    )


def build_creation_preview(
    manager: BrandManager,
    voice: Optional[VoiceExtraction],
    brand: Optional[BrandExtraction],
    name_hint: str = "",
    usage: Optional["ExtractUsage"] = None,
) -> CreationPreview:
    """
    Dựng toàn bộ đề xuất cho một brand chưa tồn tại.

    Không chạm đĩa ngoài việc kiểm mã brand đã bị dùng chưa.
    """
    name = (name_hint or "").strip()
    if not name and brand is not None:
        name = (brand.brand_name or "").strip()
    if not name:
        name = "Brand mới"

    suggested_id = slugify_brand_id(name)

    description = ""
    if brand is not None:
        description = (brand.short_description or "").strip()

    # Brand chưa tồn tại nên không có gì để đối chiếu — dựng draft với một
    # manager "rỗng" bằng cách dùng brand_id chưa có thật.
    parts = []
    if voice is not None:
        parts.append(build_voice_draft(manager, suggested_id, name, voice))
    if brand is not None:
        parts.append(build_brand_draft(manager, suggested_id, name, brand))

    draft = _merge_drafts(*parts)
    if usage is not None:
        draft.usage = usage

    from src.knowledge.brand_manager import completeness_from_contents

    completeness = completeness_from_contents({f.path: f.content for f in draft.files})

    return CreationPreview(
        identity=BrandIdentityProposal(
            name=name,
            suggested_id=suggested_id,
            description=description,
            id_taken=manager.get_brand(suggested_id) is not None,
        ),
        draft=draft,
        completeness=completeness,
    )


def extract_for_creation(
    samples: list[str], documents: list[str]
) -> tuple[Optional[VoiceExtraction], Optional[BrandExtraction], "ExtractUsage"]:
    """
    Chạy hai chặng song song. Thiếu loại tài liệu nào thì bỏ qua chặng đó —
    một trong hai là đủ để tạo brand.

    Hai prompt có lập trường ngược nhau (một cái mô tả cách brand đang viết,
    một cái coi tài liệu là nguồn sự thật) nên cố tình KHÔNG gộp thành một
    lượt gọi.
    """
    from concurrent.futures import ThreadPoolExecutor

    samples = [s for s in samples if s.strip()]
    documents = [d for d in documents if d.strip()]
    if not samples and not documents:
        raise ValueError("Chưa có tài liệu nào để đọc.")

    check_input_size(samples + documents)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_voice = pool.submit(extract_voice, samples) if samples else None
        fut_brand = pool.submit(extract_brand, documents) if documents else None

        voice, voice_usage = fut_voice.result() if fut_voice else (None, None)
        brand, brand_usage = fut_brand.result() if fut_brand else (None, None)

    usage = ExtractUsage(cached=True)
    for u in (voice_usage, brand_usage):
        if u is not None:
            usage = usage.add(u)

    return voice, brand, usage


def create_brand_from_draft(
    manager: BrandManager,
    brand_id: str,
    name: str,
    description: str,
    draft_files: list[FileDraft],
    voice_profile: Optional[dict] = None,
    brand_meta: Optional[dict] = None,
    sources: Optional[dict[str, str]] = None,
    icon: str = "📦",
    color: str = "#6c5ce7",
) -> dict:
    """
    Tạo brand rồi ghi phần đã duyệt, theo đúng thứ tự đó.

    Nếu ghi hỏng giữa chừng, brand vẫn tồn tại và người dùng bấm lưu lại được
    từ tab Nạp liệu — bản draft nằm ở trình duyệt nên không phải trả tiền đọc
    lại lần nữa. Vì thế ở đây KHÔNG xoá brand khi lỗi: xoá đi mới là mất.
    """
    manager.create_brand(brand_id, name, description, color=color, icon=icon)

    if voice_profile:
        voice_profile = {**voice_profile, "profile_id": brand_id}

    result = apply_draft(
        manager, brand_id, draft_files, voice_profile=voice_profile, brand_meta=brand_meta
    )

    result["written"].extend(_save_sources(manager, brand_id, sources))
    result["brand_id"] = brand_id
    logger.info("Tạo brand %s từ tài liệu: %s", brand_id, ", ".join(result["written"]))
    return result
