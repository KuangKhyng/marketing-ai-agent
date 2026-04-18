"""
PipelineRunner — Manual orchestration for Streamlit Web UI.

Calls each node directly instead of using LangGraph interrupt(),
because Streamlit's synchronous rerun model is incompatible with
LangGraph's async interrupt mechanism.
"""
from src.nodes.brief_parser import brief_parser_node
from src.nodes.context_builder import context_builder_node
from src.nodes.strategist import strategist_node
from src.nodes.message_architect import message_architect_node
from src.nodes.channel_renderer import channel_renderer_node
from src.nodes.reviewer import reviewer_node
from src.nodes.formatter import formatter_node
from src.models.trace import RunTrace

MAX_STRATEGY_REVISIONS = 3
MAX_CONTENT_REVISIONS = 2


class PipelineRunner:
    """Manages multi-gate pipeline execution for Web UI."""

    def __init__(self):
        self.state = None

    def phase_1_parse(self, campaign_input: str) -> dict:
        """Parse brief + build context. Returns state for brief review."""
        self.state = self._init_state(campaign_input)

        self.state.update(brief_parser_node(self.state))
        if self.state.get("error"):
            return self.state

        self.state.update(context_builder_node(self.state))
        return self.state

    def phase_2_strategy(self, feedback: str = None) -> dict:
        """Generate strategy. Accepts optional feedback for revision."""
        if feedback:
            self.state["strategy_feedback"] = feedback
        else:
            self.state["strategy_feedback"] = None

        self.state.update(strategist_node(self.state))
        return self.state

    def phase_3_content(self, feedback: str = None) -> dict:
        """Generate content. Accepts optional feedback for revision."""
        if feedback:
            self._inject_revision_feedback(feedback)

        self.state["human_approved"] = True
        self.state.update(message_architect_node(self.state))
        if self.state.get("error"):
            return self.state

        self.state.update(channel_renderer_node(self.state))
        return self.state

    def phase_4_review(self) -> dict:
        """Run automated review."""
        self.state.update(reviewer_node(self.state))
        return self.state

    def phase_5_export(self) -> dict:
        """Format and save final output."""
        self.state.update(formatter_node(self.state))
        return self.state

    def update_brief(self, updated_brief) -> None:
        """Update brief after user edits in Gate 1."""
        self.state["brief"] = updated_brief
        # Re-run context builder with updated brief
        self.state.update(context_builder_node(self.state))

    def update_content_piece(self, piece_index: int, new_body: str) -> None:
        """Update a specific content piece after user inline edit."""
        pieces = self.state["campaign_content"].pieces
        if 0 <= piece_index < len(pieces):
            pieces[piece_index].body = new_body
            pieces[piece_index].word_count = len(new_body.split())

    def _init_state(self, campaign_input: str) -> dict:
        return {
            "raw_input": campaign_input,
            "brief": None,
            "context_pack": None,
            "strategy": None,
            "strategy_feedback": None,
            "human_approved": False,
            "master_message": None,
            "campaign_content": None,
            "review_result": None,
            "revision_count": 0,
            "max_revisions": MAX_CONTENT_REVISIONS,
            "trace": RunTrace(),
            "current_node": "",
            "error": None,
        }

    def _inject_revision_feedback(self, feedback: str) -> None:
        """Inject user feedback as synthetic review result for content revision."""
        from src.models.review import ReviewResult, DimensionScore, ReviewDimension
        self.state["review_result"] = ReviewResult(
            overall_passed=False,
            dimension_scores=[
                DimensionScore(dimension=d, score=0.5, passed=False, feedback="User revision")
                for d in ReviewDimension
            ],
            revision_instructions=feedback,
            critical_issues=[],
        )


def compile_content_feedback(piece_feedback: dict) -> str:
    """Compile per-piece feedback into revision instructions."""
    parts = ["User đã review content và yêu cầu sửa các piece sau:\n"]
    for key, fb in piece_feedback.items():
        if fb.get("needs_change"):
            parts.append(f"- [{fb['channel']}/{fb['deliverable']}]: {fb.get('comment', 'Cần sửa')}")
    parts.append("\nChỉ sửa các piece được yêu cầu. Giữ nguyên các piece đã OK.")
    return "\n".join(parts)
