from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class CampaignGoal(str, Enum):
    AWARENESS = "awareness"
    ENGAGEMENT = "engagement"
    LEAD_GENERATION = "lead_generation"
    CONVERSION = "conversion"
    RETENTION = "retention"


class AwarenessStage(str, Enum):
    UNAWARE = "unaware"
    PROBLEM_AWARE = "problem_aware"
    SOLUTION_AWARE = "solution_aware"
    PRODUCT_AWARE = "product_aware"
    MOST_AWARE = "most_aware"


class Channel(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


class Deliverable(str, Enum):
    POST = "post"
    CAROUSEL = "carousel"
    REELS_SCRIPT = "reels_script"
    SHORT_VIDEO_SCRIPT = "short_video_script"
    STORY = "story"


class AudienceSpec(BaseModel):
    persona_description: str = Field(description="Mô tả ngắn gọn target audience")
    age_range: Optional[str] = None
    pain_points: list[str] = Field(default_factory=list)
    awareness_stage: AwarenessStage = AwarenessStage.PROBLEM_AWARE


class BrandSpec(BaseModel):
    name: str
    voice_profile_id: str = "default"
    forbidden_claims: list[str] = Field(default_factory=list, description="Những claim KHÔNG được đưa vào content")
    mandatory_terms: list[str] = Field(default_factory=list, description="Từ/cụm từ BẮT BUỘC phải có")


class OfferSpec(BaseModel):
    product_or_service: str = Field(description="Tên sản phẩm/dịch vụ")
    key_message: str = Field(description="Thông điệp chính muốn truyền tải")
    cta: str = Field(description="Call-to-action mong muốn")
    unique_selling_points: list[str] = Field(default_factory=list)


class ContentConstraints(BaseModel):
    word_limit: Optional[int] = None
    must_include: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)
    hashtag_count: Optional[int] = None


class SuccessCriteria(BaseModel):
    tone_match_min: float = Field(default=0.7, ge=0, le=1, description="Minimum tone match score")
    factuality_required: bool = True
    brand_safety_required: bool = True


class CampaignBrief(BaseModel):
    """Canonical brief schema — single source of truth cho toàn pipeline."""
    goal: CampaignGoal
    brand: BrandSpec
    audience: AudienceSpec
    offer: OfferSpec
    channels: list[Channel]
    deliverables: list[Deliverable]
    constraints: ContentConstraints = Field(default_factory=ContentConstraints)
    success_criteria: SuccessCriteria = Field(default_factory=SuccessCriteria)
    additional_context: Optional[str] = None
