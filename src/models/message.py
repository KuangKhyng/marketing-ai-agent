from pydantic import BaseModel, Field
from typing import Optional


class MasterMessage(BaseModel):
    """Platform-agnostic message architecture — bộ khung cho tất cả content."""
    core_promise: str = Field(description="Lời hứa cốt lõi — 1 câu, CỤ THỂ, có tension")
    
    tension: str = Field(
        default="",
        description="Mâu thuẫn/vấn đề chưa ai nói ra mà audience đang cảm nhận"
    )
    
    key_points: list[str] = Field(
        description="3-5 điểm chính, mỗi điểm phải có substance và WHY",
        min_length=1, max_length=5
    )
    
    emotional_journey: str = Field(
        default="",
        description="Hành trình cảm xúc: audience cảm thấy [A] → [B] → [C]"
    )
    
    emotional_angle: str = Field(description="Góc cảm xúc muốn chạm")
    
    proof_elements: list[str] = Field(
        default_factory=list,
        description="Bằng chứng cụ thể: số liệu, case study, social proof"
    )
    proof_angle: str = Field(default="", description="Góc proof chung — backward compat")
    
    unique_angle: str = Field(
        default="",
        description="Góc nhìn chỉ content này có — khác 100 bài cùng topic"
    )
    
    storytelling_seed: str = Field(
        default="",
        description="Micro-story hoặc scenario cụ thể để Channel Renderer phát triển"
    )
    
    cta_primary: str = Field(description="CTA chính")
    cta_secondary: Optional[str] = Field(default=None, description="CTA phụ (lower commitment)")
    
    taboo_points: list[str] = Field(default_factory=list, description="Không đề cập")
    tone_direction: str = Field(description="Hướng dẫn tone cụ thể bằng ví dụ")
    
    copywriting_framework: str = Field(
        default="PAS",
        description="Framework cho Channel Renderer: PAS / BAB / AIDA"
    )
