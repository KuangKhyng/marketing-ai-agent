from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class ReviewDimension(str, Enum):
    BRAND_FIT = "brand_fit"
    FACTUALITY = "factuality"
    CHANNEL_FIT = "channel_fit"
    BUSINESS_FIT = "business_fit"
    CONTENT_DEPTH = "content_depth"    # NEW


# === Schema cho LLM ===
#
# Tách khỏi ReviewResult vì ReviewResult chứa những field do CODE quyết định:
# `passed` (so với ngưỡng), `overall_passed`, `rule_violations`, `review_unavailable`.
# Nếu để chúng trong schema truyền cho with_structured_output thì LLM sẽ tự
# điền và code phải ném đi — vừa tốn token vừa dễ nhầm là ý kiến của LLM.


class LLMDimensionScore(BaseModel):
    """Điểm một chiều do Claude chấm. Không có `passed` — ngưỡng do code áp."""
    dimension: ReviewDimension
    score: float = Field(ge=0, le=1, description="0.0 = hoàn toàn sai, 1.0 = hoàn hảo")
    feedback: str = Field(description="Lý do cụ thể cho điểm này")


class LLMReviewOutput(BaseModel):
    """Đúng những gì Claude cần trả về. Phải đủ cả 5 dimension."""
    dimension_scores: list[LLMDimensionScore] = Field(
        description="Bắt buộc đủ 5 dimension: brand_fit, factuality, channel_fit, "
                    "business_fit, content_depth"
    )
    critical_issues: list[str] = Field(default_factory=list, description="Vấn đề nghiêm trọng cần sửa ngay")
    suggestions: list[str] = Field(default_factory=list, description="Đề xuất cải thiện (không bắt buộc)")
    revision_instructions: Optional[str] = Field(default=None, description="Hướng dẫn sửa cụ thể nếu có vấn đề")


# === Schema nội bộ / trả về cho UI ===


class DimensionScore(BaseModel):
    dimension: ReviewDimension
    score: float = Field(ge=0, le=1, description="0.0 = hoàn toàn sai, 1.0 = hoàn hảo")
    passed: bool
    feedback: str = Field(description="Lý do cụ thể nếu không pass")
    rule_violations: list[str] = Field(
        default_factory=list,
        description="Vi phạm quy tắc cứng thuộc chiều này (kiểm bằng code, không phải ý kiến LLM)",
    )


class ReviewResult(BaseModel):
    overall_passed: bool
    dimension_scores: list[DimensionScore]
    critical_issues: list[str] = Field(default_factory=list, description="Vấn đề nghiêm trọng cần sửa ngay")
    suggestions: list[str] = Field(default_factory=list, description="Đề xuất cải thiện (không bắt buộc)")
    revision_instructions: Optional[str] = Field(default=None, description="Hướng dẫn sửa cụ thể nếu fail")
    review_unavailable: bool = Field(
        default=False,
        description="Reviewer lỗi nên CHƯA chấm được. Khác hoàn toàn với 'đã chấm và không đạt'.",
    )
