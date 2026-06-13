"""
Pipeline Runner — wraps existing nodes into callable phases.
Used by FastAPI endpoints. Does NOT use LangGraph interrupt().

SOURCE OF TRUTH: This is the only PipelineRunner. src/web/pipeline.py đã bị xóa.
"""
from typing import Callable, Optional

from src.nodes.brief_parser import brief_parser_node
from src.nodes.context_builder import context_builder_node
from src.nodes.strategist import strategist_node
from src.nodes.message_architect import message_architect_node
from src.nodes.channel_renderer import channel_renderer_node
from src.nodes.reviewer import reviewer_node
from src.nodes.formatter import formatter_node
from src.models.trace import RunTrace
from src.models.brief import CampaignBrief, CampaignGoal, BrandSpec, AudienceSpec, OfferSpec, Channel, Deliverable
from src.models.review import ReviewResult, DimensionScore, ReviewDimension

_ProgressFn = Optional[Callable[[dict], None]]

_NODE_MESSAGES = {
    "brief_parser":      "Đang phân tích yêu cầu...",
    "context_builder":   "Đang tải thông tin brand & platform...",
    "strategist":        "Đang xây dựng chiến lược campaign...",
    "message_architect": "Đang tạo message architecture...",
    "channel_renderer":  "Đang viết content cho từng platform...",
    "reviewer":          "Đang kiểm tra chất lượng nội dung...",
    "formatter":         "Đang xuất kết quả...",
}


def _emit(on_progress: _ProgressFn, node: str, done: bool = False) -> None:
    if not on_progress:
        return
    event = {
        "type": "node_done" if done else "node_start",
        "node": node,
    }
    if not done:
        event["message"] = _NODE_MESSAGES.get(node, f"Running {node}...")
    on_progress(event)


class PipelineRunner:
    def __init__(self):
        self.state = None

    def phase_1_parse(self, raw_input: str, brand_id: str = None, on_progress: _ProgressFn = None) -> dict:
        self.state = self._init_state(raw_input, brand_id=brand_id)

        _emit(on_progress, "brief_parser")
        self.state.update(brief_parser_node(self.state))
        _emit(on_progress, "brief_parser", done=True)
        if self.state.get("error"):
            return self.state

        _emit(on_progress, "context_builder")
        self.state.update(context_builder_node(self.state))
        _emit(on_progress, "context_builder", done=True)
        return self.state

    def phase_2_strategy(self, feedback: str = None, on_progress: _ProgressFn = None) -> dict:
        if feedback:
            self.state["strategy_feedback"] = feedback
        _emit(on_progress, "strategist")
        self.state.update(strategist_node(self.state))
        _emit(on_progress, "strategist", done=True)
        return self.state

    def phase_3_content(self, feedback: str = None, on_progress: _ProgressFn = None) -> dict:
        if feedback:
            self.state["review_result"] = ReviewResult(
                overall_passed=False,
                dimension_scores=[
                    DimensionScore(dimension=d, score=0.5, passed=False, feedback="User revision")
                    for d in ReviewDimension
                ],
                revision_instructions=feedback,
                critical_issues=[],
            )
        self.state["human_approved"] = True

        _emit(on_progress, "message_architect")
        self.state.update(message_architect_node(self.state))
        _emit(on_progress, "message_architect", done=True)
        if self.state.get("error"):
            return self.state

        _emit(on_progress, "channel_renderer")
        self.state.update(channel_renderer_node(self.state))
        _emit(on_progress, "channel_renderer", done=True)
        return self.state

    def phase_4_review(self, on_progress: _ProgressFn = None) -> dict:
        _emit(on_progress, "reviewer")
        self.state.update(reviewer_node(self.state))
        _emit(on_progress, "reviewer", done=True)
        return self.state

    def phase_5_export(self) -> dict:
        self.state.update(formatter_node(self.state))
        return self.state

    def update_brief_fields(self, edit) -> None:
        brief = self.state["brief"]
        if edit.goal:
            brief.goal = CampaignGoal(edit.goal)
        if edit.product:
            brief.offer.product_or_service = edit.product
        if edit.audience:
            brief.audience.persona_description = edit.audience
        if edit.channels:
            brief.channels = [Channel(c) for c in edit.channels]
        if edit.key_message:
            brief.offer.key_message = edit.key_message
        if edit.cta:
            brief.offer.cta = edit.cta
        # Re-build context with updated brief
        self.state.update(context_builder_node(self.state))

    def update_content_piece(self, index: int, new_body: str) -> None:
        pieces = self.state["campaign_content"].pieces
        if 0 <= index < len(pieces):
            pieces[index].body = new_body
            pieces[index].word_count = len(new_body.split())

    def _init_state(self, raw_input: str, brand_id: str = None) -> dict:
        return {
            "raw_input": raw_input,
            "brand_id": brand_id,
            "brief": None,
            "context_pack": None,
            "strategy": None,
            "strategy_feedback": None,
            "human_approved": False,
            "master_message": None,
            "campaign_content": None,
            "review_result": None,
            "revision_count": 0,
            "max_revisions": 2,
            "trace": RunTrace(),
            "current_node": "",
            "error": None,
        }
