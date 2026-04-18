from pydantic import BaseModel, Field
from typing import Optional


class MasterMessage(BaseModel):
    """Platform-agnostic message architecture — bộ xương cho tất cả content."""
    core_promise: str = Field(description="Lời hứa cốt lõi — 1 câu duy nhất")
    key_points: list[str] = Field(description="3-5 điểm chính hỗ trợ core promise", min_length=1, max_length=5)
    emotional_angle: str = Field(description="Góc cảm xúc muốn chạm — ví dụ: tò mò, an tâm, FOMO")
    proof_angle: str = Field(description="Bằng chứng/social proof hỗ trợ — ví dụ: số liệu, testimonial")
    cta_primary: str = Field(description="CTA chính")
    cta_secondary: Optional[str] = Field(default=None, description="CTA phụ (nếu có)")
    taboo_points: list[str] = Field(default_factory=list, description="Những điều TUYỆT ĐỐI KHÔNG đề cập")
    tone_direction: str = Field(description="Hướng dẫn tone cụ thể cho content này")
