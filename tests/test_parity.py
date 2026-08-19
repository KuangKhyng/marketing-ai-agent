"""
Chống lệch giữa hai pipeline.

Repo có hai đường thực thi cùng một dây chuyền:
  - src/graph/workflow.py  (LangGraph)         -> cli.py dùng
  - api/pipeline_runner.py (gọi node trực tiếp) -> web dùng

Không có gì bắt chúng phải giống nhau, và chúng ĐÃ lệch: vòng sửa lại khi
review trượt chỉ tồn tại ở nhánh graph. Test này chạy cùng một brief qua cả
hai và so thứ tự node + kết quả cuối, để lần sau lệch là biết ngay.

Mọi node LLM đều là hàm giả — không gọi API thật.
"""
import pytest
from langgraph.types import Command

import api.pipeline_runner as pr
import src.graph.workflow as wf
from api.pipeline_runner import PipelineRunner
from src.graph.workflow import build_workflow
from src.models.content import CampaignContent, ContentPiece
from src.models.brief import Channel, Deliverable
from src.models.review import DimensionScore, ReviewDimension, ReviewResult
from src.models.trace import RunTrace


# Node chỉ có ở nhánh graph: nhánh web để tầng HTTP làm việc duyệt của con
# người (SessionStore + endpoint), nên không có node tương ứng.
GRAPH_ONLY_NODES = {"human_approval"}


def _piece():
    return ContentPiece(
        channel=Channel.FACEBOOK,
        deliverable=Deliverable.POST,
        body="Nội dung mẫu " * 40,
        cta_text="Ghé quán",
        word_count=200,
    )


def _review(passed: bool):
    return ReviewResult(
        overall_passed=passed,
        dimension_scores=[
            DimensionScore(
                dimension=d,
                score=0.9 if passed else 0.4,
                passed=passed,
                feedback="ok" if passed else "chưa đủ sâu",
            )
            for d in ReviewDimension
        ],
        revision_instructions=None if passed else "Viết sâu hơn",
    )


def make_fakes(brief, master_message, review_outcomes):
    """
    Trả về (fakes, trace) — dict node giả dùng được cho CẢ HAI nhánh.

    review_outcomes: list bool, kết quả review lần 1, lần 2, ...
    trace: list tên node đã chạy, theo thứ tự.
    """
    trace = []
    outcomes = list(review_outcomes)

    def brief_parser(state):
        trace.append("brief_parser")
        return {"brief": brief.model_copy(deep=True), "current_node": "brief_parser"}

    def context_builder(state):
        trace.append("context_builder")
        return {"context_pack": {"mode": "generic"}, "current_node": "context_builder"}

    def strategist(state):
        trace.append("strategist")
        return {"strategy": "Chiến lược", "current_node": "strategist"}

    def message_architect(state):
        trace.append("message_architect")
        return {
            "master_message": master_message.model_copy(deep=True),
            "current_node": "message_architect",
        }

    def channel_renderer(state):
        trace.append("channel_renderer")
        return {
            "campaign_content": CampaignContent(
                pieces=[_piece()], master_message_summary="x"
            ),
            "warnings": [],
            "current_node": "channel_renderer",
        }

    def reviewer(state):
        trace.append("reviewer")
        passed = outcomes.pop(0) if outcomes else True
        result = _review(passed)
        revision_count = state.get("revision_count", 0)
        if not passed:
            revision_count += 1
        return {
            "review_result": result,
            "revision_count": revision_count,
            "current_node": "reviewer",
        }

    def formatter(state):
        trace.append("formatter")
        return {"current_node": "formatter"}

    return {
        "brief_parser_node": brief_parser,
        "context_builder_node": context_builder,
        "strategist_node": strategist,
        "message_architect_node": message_architect,
        "channel_renderer_node": channel_renderer,
        "reviewer_node": reviewer,
        "formatter_node": formatter,
    }, trace


def _install(monkeypatch, module, fakes):
    """
    Cả hai module đều `from src.nodes.X import Y`, tức là đã bind hàm lúc
    import. Nên phải patch tên trong TỪNG module, không patch được ở nguồn.
    """
    for name, fn in fakes.items():
        monkeypatch.setattr(module, name, fn)


def run_graph(monkeypatch, brief, master_message, review_outcomes):
    fakes, trace = make_fakes(brief, master_message, review_outcomes)
    _install(monkeypatch, wf, fakes)

    workflow = build_workflow()
    config = {"configurable": {"thread_id": "parity-test"}}

    initial = {
        "raw_input": "cà phê rang mộc",
        "brand_id": None,
        "human_approved": False,
        "revision_count": 0,
        "max_review_attempts": 2,
        "trace": RunTrace(),
        "current_node": "",
        "error": None,
        "warnings": [],
        "review_route": None,
    }

    workflow.invoke(initial, config=config)               # dừng ở interrupt
    final = workflow.invoke(Command(resume={"approved": True}), config=config)

    return [n for n in trace if n not in GRAPH_ONLY_NODES], final


def run_runner(monkeypatch, brief, master_message, review_outcomes):
    fakes, trace = make_fakes(brief, master_message, review_outcomes)
    _install(monkeypatch, pr, fakes)

    runner = PipelineRunner()
    runner.phase_1_parse("cà phê rang mộc")
    runner.phase_2_strategy()
    runner.phase_3_content()
    runner.phase_4_review()

    # Nhánh graph tự vòng lại khi route == "retry"; ở đây gọi tay cho tương
    # đương, dùng đúng hàm routing mà graph dùng.
    while runner.can_retry():
        runner.retry_content()

    runner.phase_5_export()
    return trace, runner.state


class TestParity:
    def test_review_pass_ngay_lan_dau(self, brief, master_message, monkeypatch):
        graph_trace, graph_state = run_graph(monkeypatch, brief, master_message, [True])
        runner_trace, runner_state = run_runner(monkeypatch, brief, master_message, [True])

        assert graph_trace == runner_trace, (
            f"Thứ tự node lệch nhau:\n  graph : {graph_trace}\n  runner: {runner_trace}"
        )
        assert graph_trace == [
            "brief_parser",
            "context_builder",
            "strategist",
            "message_architect",
            "channel_renderer",
            "reviewer",
            "formatter",
        ]
        assert graph_state["review_result"].overall_passed is True
        assert runner_state["review_result"].overall_passed is True

    def test_review_truot_mot_lan_roi_dat(self, brief, master_message, monkeypatch):
        """Đây chính là chỗ trước đây lệch: nhánh web không có vòng sửa lại."""
        outcomes = [False, True]
        graph_trace, graph_state = run_graph(monkeypatch, brief, master_message, outcomes)
        runner_trace, runner_state = run_runner(monkeypatch, brief, master_message, outcomes)

        assert graph_trace == runner_trace, (
            f"Vòng sửa lại lệch nhau:\n  graph : {graph_trace}\n  runner: {runner_trace}"
        )
        # message_architect -> channel_renderer -> reviewer chạy hai lượt
        assert graph_trace.count("reviewer") == 2
        assert graph_trace.count("message_architect") == 2
        assert graph_trace[-1] == "formatter"

        assert graph_state["revision_count"] == runner_state["revision_count"] == 1
        assert runner_state["review_result"].overall_passed is True

    def test_truot_het_luot_van_xuat_ban(self, brief, master_message, monkeypatch):
        """
        Trượt mãi thì cả hai đều dừng đúng chỗ và vẫn đi formatter.

        Về con số: max_review_attempts=2 là số lượt CHẤM, cho đúng MỘT lượt sửa.
        reviewer tăng revision_count mỗi lần trượt, rồi route_after_review so
        `revision_count < max_review_attempts`:
            reviewer #1 -> count 1, 1 < 2 -> retry
            reviewer #2 -> count 2, 2 < 2 sai -> max_retries -> formatter
        Tên biến hơi lệch nghĩa nhưng hai nhánh lệch nhau thì tệ hơn, nên test
        chốt hành vi hiện tại chứ không đổi nó.
        """
        outcomes = [False, False, False, False]
        graph_trace, graph_state = run_graph(monkeypatch, brief, master_message, outcomes)
        runner_trace, runner_state = run_runner(monkeypatch, brief, master_message, outcomes)

        assert graph_trace == runner_trace, (
            f"Ngưỡng hết lượt lệch nhau:\n  graph : {graph_trace}\n  runner: {runner_trace}"
        )
        assert graph_trace.count("reviewer") == 2       # lần đầu + 1 lượt sửa
        assert graph_trace.count("message_architect") == 2
        assert graph_trace[-1] == "formatter"
        assert graph_state["revision_count"] == runner_state["revision_count"] == 2
        assert runner_state["review_route"] == "max_retries"

    def test_runner_khong_tu_retry(self, brief, master_message, monkeypatch):
        """
        Khác biệt CÓ CHỦ Ý: runner không tự vòng lại, chỉ báo route ra ngoài.
        Mỗi vòng là một lượt gọi API tốn tiền nên web hỏi người dùng trước.
        """
        fakes, trace = make_fakes(brief, master_message, [False, True])
        _install(monkeypatch, pr, fakes)

        runner = PipelineRunner()
        runner.phase_1_parse("x")
        runner.phase_2_strategy()
        runner.phase_3_content()
        runner.phase_4_review()

        assert runner.state["review_route"] == "retry"
        assert trace.count("reviewer") == 1, "phase_4_review không được tự sửa lại"
        assert runner.can_retry() is True
