from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class ReviewDimension(str, Enum):
    BRAND_FIT = "brand_fit"
    FACTUALITY = "factuality"
    CHANNEL_FIT = "channel_fit"
    BUSINESS_FIT = "business_fit"
    CONTENT_DEPTH = "content_depth"    # NEW


class DimensionScore(BaseModel):
    dimension: ReviewDimension
    score: float = Field(ge=0, le=1, description="0.0 = hoàn toàn sai, 1.0 = hoàn hảo")
    passed: bool
    feedback: str = Field(description="Lý do cụ thể nếu không pass")


class ReviewResult(BaseModel):
    overall_passed: bool
    dimension_scores: list[DimensionScore]
    critical_issues: list[str] = Field(default_factory=list, description="Vấn đề nghiêm trọng cần sửa ngay")
    suggestions: list[str] = Field(default_factory=list, description="Đề xuất cải thiện (không bắt buộc)")
    revision_instructions: Optional[str] = Field(default=None, description="Hướng dẫn sửa cụ thể nếu fail")
