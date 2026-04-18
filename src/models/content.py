from pydantic import BaseModel, Field
from typing import Optional
from .brief import Channel, Deliverable


class ContentPiece(BaseModel):
    """Một piece content cho một platform cụ thể."""
    channel: Channel
    deliverable: Deliverable
    headline: Optional[str] = None
    body: str = Field(description="Nội dung chính")
    hashtags: list[str] = Field(default_factory=list)
    visual_direction: Optional[str] = Field(default=None, description="Gợi ý hình ảnh/video")
    hook: Optional[str] = Field(default=None, description="Opening hook (đặc biệt quan trọng cho TikTok/Reels)")
    cta_text: str = ""
    notes: Optional[str] = Field(default=None, description="Ghi chú thêm cho content creator")
    word_count: int = 0


class CampaignContent(BaseModel):
    """Tập hợp tất cả content pieces cho một campaign."""
    pieces: list[ContentPiece]
    master_message_summary: str = Field(description="Tóm tắt message architecture để reference")
