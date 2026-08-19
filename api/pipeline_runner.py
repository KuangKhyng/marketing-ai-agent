"""
Pipeline Runner — bọc các node thành từng phase gọi được.

Dùng bởi FastAPI. KHÔNG dùng LangGraph interrupt() vì tầng HTTP tự quản phiên
làm việc (xem SessionStore trong api/routes/campaign.py).

QUAN HỆ VỚI src/graph/:
    Cùng gọi CÙNG các node trong src/nodes/ và CÙNG hàm routing
    src/graph/edges.route_after_review. Thứ tự node phải khớp workflow.py —
    tests/test_parity.py chạy cùng một brief qua cả hai đường và so kết quả để
    phát hiện lệch.

    Khác biệt DUY NHẤT là chủ ý: khi review trượt, graph tự vòng lại
    message_architect; runner trả route ra cho người dùng quyết (xem
    retry_content). Vì mỗi lần vòng lại là tốn tiền API nên web hỏi trước.
"""
import logging
from datetime import datetime
from typing import Callable, Optional

from src.graph.edges import route_after_review
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

logger = logging.getLogger(__name__)

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

    def _begin_attempt(self, phase: str) -> None:
        """
        Bắt đầu một lượt chạy mới.

        Lỗi thuộc về LƯỢT CHẠY, không thuộc về phiên. Mọi node đều mở đầu bằng
        `if state.get("error"): return`, nên nếu không xoá ở đây thì một lần
        Anthropic timeout sẽ giết phiên vĩnh viễn: user bấm Retry bao nhiêu lần
        cũng chỉ nhận lại đúng lỗi cũ vì node nào cũng return ngay.

        Lỗi cũ được giữ trong `last_error` để còn truy được, chứ không mất.
        """
        loi_cu = self.state.get("error")
        if loi_cu:
            self.state["last_error"] = {
                "phase": self.state.get("current_phase") or self.state.get("current_node"),
                "message": loi_cu,
                "at": datetime.now().isoformat(),
            }
            logger.info("Chạy lại phase %s sau lỗi trước đó: %s", phase, loi_cu)

        self.state["error"] = None
        self.state["current_phase"] = phase
        self.state["attempt"] = self.state.get("attempt", 0) + 1

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
        self._begin_attempt("strategy")
        if feedback:
            self.state["strategy_feedback"] = feedback
        _emit(on_progress, "strategist")
        self.state.update(strategist_node(self.state))
        _emit(on_progress, "strategist", done=True)
        return self.state

    def phase_3_content(self, feedback: str = None, on_progress: _ProgressFn = None) -> dict:
        self._begin_attempt("content")
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
        self._begin_attempt("review")
        _emit(on_progress, "reviewer")
        self.state.update(reviewer_node(self.state))
        _emit(on_progress, "reviewer", done=True)

        # Cùng hàm mà graph dùng ở conditional edge sau reviewer. Ở đây chỉ
        # LƯU quyết định chứ không tự đi tiếp — người dùng bấm mới đi.
        #   "passed"      -> xuất bản được
        #   "retry"       -> nên sửa lại, còn lượt
        #   "max_retries" -> hết lượt sửa, muốn xuất thì phải tự chịu
        self.state["review_route"] = route_after_review(self.state)
        return self.state

    def retry_content(self, on_progress: _ProgressFn = None) -> dict:
        """
        Làm đúng việc nhánh "retry" của graph: quay lại message_architect với
        revision_instructions của reviewer, rồi render và chấm lại.

        Graph làm tự động; ở đây phải do người dùng bấm.
        """
        self._begin_attempt("content")

        # Giữ nguyên review_result để message_architect đọc được feedback,
        # y như graph (graph không xoá review_result khi vòng lại).
        _emit(on_progress, "message_architect")
        self.state.update(message_architect_node(self.state))
        _emit(on_progress, "message_architect", done=True)
        if self.state.get("error"):
            return self.state

        _emit(on_progress, "channel_renderer")
        self.state.update(channel_renderer_node(self.state))
        _emit(on_progress, "channel_renderer", done=True)
        if self.state.get("error"):
            return self.state

        return self.phase_4_review(on_progress=on_progress)

    def can_retry(self) -> bool:
        """Còn lượt sửa lại không — cùng ngưỡng mà graph dùng."""
        return self.state.get("review_route") == "retry"

    def phase_5_export(self) -> dict:
        self._begin_attempt("export")
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
            "warnings": [],
            "review_route": None,
            "current_phase": None,
            "attempt": 0,
            "last_error": None,
        }
