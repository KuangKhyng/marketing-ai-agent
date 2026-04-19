from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# === REQUEST SCHEMAS ===

class CampaignInput(BaseModel):
    """Input for starting a new campaign."""
    mode: str = "free_text"  # "free_text" | "structured"

    # Brand selection (None = generic mode)
    brand_id: Optional[str] = None

    # Free text mode
    raw_input: Optional[str] = None

    # Structured mode
    goal: Optional[str] = None
    product: Optional[str] = None
    audience: Optional[str] = None
    channels: Optional[list[str]] = None
    key_message: Optional[str] = None
    cta: Optional[str] = None

    # Language preference
    language: str = "vi"  # "vi" | "en"

    def to_raw_input(self) -> str:
        if self.mode == "free_text" and self.raw_input:
            raw = self.raw_input
            if self.language == "en":
                raw += "\n\n[LANGUAGE INSTRUCTION: Generate ALL content in English. Do NOT use Vietnamese.]"
            return raw
        parts = []
        if self.goal: parts.append(f"Tạo campaign {self.goal}")
        if self.product: parts.append(f"cho {self.product}")
        if self.audience: parts.append(f"target {self.audience}")
        if self.channels: parts.append(f"Channels: {', '.join(self.channels)}")
        if self.key_message: parts.append(f"Key message: {self.key_message}")
        if self.cta: parts.append(f"CTA: {self.cta}")
        raw = ". ".join(parts)
        if self.language == "en":
            raw += "\n\n[LANGUAGE INSTRUCTION: Generate ALL content in English. Do NOT use Vietnamese.]"
        return raw


class BriefEdit(BaseModel):
    """User edits to the parsed brief."""
    goal: Optional[str] = None
    product: Optional[str] = None
    audience: Optional[str] = None
    channels: Optional[list[str]] = None
    key_message: Optional[str] = None
    cta: Optional[str] = None


class StrategyFeedback(BaseModel):
    """User feedback on strategy."""
    approved: bool
    feedback_checks: list[str] = Field(default_factory=list)  # ["tone", "hook", "cta", ...]
    comment: Optional[str] = None


class ContentPieceFeedback(BaseModel):
    """User feedback on a single content piece."""
    piece_index: int
    approved: bool
    comment: Optional[str] = None
    edited_body: Optional[str] = None  # If user edited directly


class ContentFeedback(BaseModel):
    """User feedback on all content."""
    approved: bool
    piece_feedbacks: list[ContentPieceFeedback] = Field(default_factory=list)


# === RESPONSE SCHEMAS ===

class ContextInfo(BaseModel):
    mode: str
    brand_name: str = ""
    loaded_docs: list[str] = []
    total_tokens_estimate: int = 0

class PipelineStatus(BaseModel):
    run_id: str
    phase: str  # "brief_review" | "strategy_review" | "content_review" | "final_review" | "completed" | "error"
    brief: Optional[dict] = None
    strategy: Optional[str] = None
    master_message: Optional[dict] = None
    content: Optional[dict] = None
    review_result: Optional[dict] = None
    error: Optional[str] = None
    revision_count: int = 0
    cost_estimate: float = 0.0
    context_info: Optional[ContextInfo] = None
