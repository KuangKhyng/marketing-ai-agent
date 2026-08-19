"""
R4 — Quick Action.

Ba lỗi được sửa ở đây:
  1. "Đổi hook" ghi vào piece.body và không bao giờ đụng piece.hook, nên hook
     hiện trên UI vẫn là hook cũ.
  2. Prompt cô lập, không có brand/product/policy/voice/master message — tức là
     đường sửa nhanh đi vòng qua mọi ràng buộc mà generator và reviewer phải
     tuân theo, rồi kết quả lại được coi là nội dung đã duyệt.
  3. Lượt gọi không vào trace, nên báo cáo chi phí nói dối.

Và một hành vi mới: sửa nội dung thì kết quả chấm cũ hết hiệu lực.
"""
import os

import pytest

os.environ["ENV"] = "dev"

from fastapi.testclient import TestClient  # noqa: E402

import api.pipeline_runner as pr  # noqa: E402
import api.routes.campaign as campaign_mod  # noqa: E402
import src.nodes.quick_action as qa  # noqa: E402
from api.main import app  # noqa: E402
from api.pipeline_runner import PipelineRunner  # noqa: E402
from src.models.brief import Channel, Deliverable  # noqa: E402
from src.models.content import CampaignContent, ContentPiece  # noqa: E402
from src.models.review import DimensionScore, ReviewDimension, ReviewResult  # noqa: E402
from src.models.trace import RunTrace  # noqa: E402


def a_piece(hook="Hook cũ", body="Thân bài cũ. " * 20):
    return ContentPiece(
        channel=Channel.FACEBOOK,
        deliverable=Deliverable.POST,
        hook=hook,
        body=body,
        cta_text="Ghé quán",
        word_count=len(body.split()),
    )


@pytest.fixture
def state(brief, master_message):
    brief.brand.forbidden_claims = ["ngon nhất Việt Nam"]
    brief.brand.mandatory_terms = ["Cà Phê ABC"]
    return {
        "brief": brief,
        "master_message": master_message,
        "context_pack": {
            "voice_profile": {"tone": {"primary": "mộc mạc"}},
            "product": "Hạt Arabica Cầu Đất, rang mỗi ngày",
            "policies": "Không cam kết chữa bệnh",
            "platform_rules": {"facebook": "Bài 150-600 từ"},
        },
        "campaign_content": CampaignContent(
            pieces=[a_piece()], master_message_summary="Rang mỗi ngày"
        ),
        "trace": RunTrace(),
    }


@pytest.fixture
def llm_gia(monkeypatch):
    """Bắt lại prompt gửi đi, và trả về kết quả điều khiển được."""
    da_gui = {}
    tra_ve = {"hook": "Hook MỚI", "body": "Thân bài MỚI. " * 20, "cta_text": ""}

    class FakeStructured:
        def invoke(self, messages, config=None):
            da_gui["system"] = messages[0].content
            da_gui["user"] = messages[1].content
            if config and config.get("callbacks"):
                for cb in config["callbacks"]:
                    cb.input_tokens += 1200
                    cb.output_tokens += 400
            return qa.QuickActionOutput(**tra_ve)

    class FakeLLM:
        def with_structured_output(self, schema):
            return FakeStructured()

    monkeypatch.setattr(qa, "ChatAnthropic", None, raising=False)
    monkeypatch.setattr(
        qa, "get_model_config",
        lambda ten: {"model": "claude-sonnet-4-6", "temperature": 0.7, "max_tokens": 3000},
    )
    monkeypatch.setattr(qa, "get_api_key", lambda: "sk-ant-test")

    import langchain_anthropic
    monkeypatch.setattr(langchain_anthropic, "ChatAnthropic", lambda **kw: FakeLLM())

    return da_gui, tra_ve


# === Bug chính: đổi hook phải đổi hook ===


def test_doi_hook_thi_hook_that_su_doi(state, llm_gia):
    out = qa.quick_action_node(state, 0, "change_hook")
    piece = out["campaign_content"].pieces[0]

    assert piece.hook == "Hook MỚI", "trước đây hook giữ nguyên còn body bị ghi đè"
    assert "Thân bài MỚI" in piece.body


def test_hook_rong_thi_de_none(state, llm_gia):
    da_gui, tra_ve = llm_gia
    tra_ve["hook"] = ""

    out = qa.quick_action_node(state, 0, "rewrite")
    assert out["campaign_content"].pieces[0].hook is None


def test_hook_trung_dong_dau_body_thi_bo(state, llm_gia):
    """Giữ đúng quy ước dedup của channel_renderer."""
    da_gui, tra_ve = llm_gia
    tra_ve["hook"] = "Cùng một câu"
    tra_ve["body"] = "Cùng một câu\nphần còn lại của bài"

    out = qa.quick_action_node(state, 0, "rewrite")
    assert out["campaign_content"].pieces[0].hook is None


# === Không được đi vòng qua ràng buộc ===


class TestKhongDiVongGuardrail:
    def test_prompt_co_du_rang_buoc_brand(self, state, llm_gia):
        da_gui, _ = llm_gia
        qa.quick_action_node(state, 0, "rewrite")

        user = da_gui["user"]
        assert "ngon nhất Việt Nam" in user, "forbidden_claims phải đi kèm"
        assert "Cà Phê ABC" in user, "mandatory_terms phải đi kèm"

    def test_prompt_co_san_pham_va_quy_dinh(self, state, llm_gia):
        da_gui, _ = llm_gia
        qa.quick_action_node(state, 0, "rewrite")

        assert "Arabica Cầu Đất" in da_gui["user"]
        assert "Không cam kết chữa bệnh" in da_gui["user"]

    def test_prompt_co_giong_va_thong_diep_coc_loi(self, state, llm_gia):
        da_gui, _ = llm_gia
        qa.quick_action_node(state, 0, "rewrite")

        assert "mộc mạc" in da_gui["user"]
        assert state["master_message"].core_promise in da_gui["user"]

    def test_prompt_co_quy_tac_nen_tang(self, state, llm_gia):
        da_gui, _ = llm_gia
        qa.quick_action_node(state, 0, "rewrite")
        assert "150-600 từ" in da_gui["user"]

    def test_moi_viec_deu_noi_ro_lam_gi(self, state, llm_gia):
        da_gui, _ = llm_gia
        for viec in qa.ACTIONS:
            qa.quick_action_node(state, 0, viec)
            assert qa.ACTIONS[viec][:30] in da_gui["user"], f"thiếu mô tả việc {viec}"


# === Chi phí phải vào trace ===


def test_lan_goi_nay_vao_trace(state, llm_gia):
    truoc = state["trace"].total_cost_estimate
    out = qa.quick_action_node(state, 0, "rewrite")

    trace = out["trace"]
    assert trace.total_cost_estimate > truoc, "quick action đốt tiền thì phải vào báo cáo"
    assert trace.node_traces[-1].node_name == "quick_action:rewrite"
    assert trace.node_traces[-1].token_usage["input"] == 1200


# === Sửa nội dung thì điểm chấm cũ hết hiệu lực ===


class TestXoaKetQuaCham:
    def _review(self):
        return ReviewResult(
            overall_passed=True,
            dimension_scores=[
                DimensionScore(dimension=d, score=0.9, passed=True, feedback="ok")
                for d in ReviewDimension
            ],
        )

    def test_quick_action_xoa_review(self, state, llm_gia):
        state["review_result"] = self._review()
        state["review_route"] = "passed"

        out = qa.quick_action_node(state, 0, "rewrite")

        assert out["review_result"] is None, (
            "giữ điểm cũ sau khi sửa là để người dùng bàn giao dựa trên một lần "
            "chấm cho bản khác"
        )
        assert out["review_route"] is None

    def test_sua_tay_cung_xoa_review(self, state, llm_gia):
        runner = PipelineRunner()
        runner.state = state
        runner.state["review_result"] = self._review()
        runner.state["review_route"] = "passed"

        runner.update_content_piece(0, "Tôi tự sửa tay đoạn này")

        assert runner.state["review_result"] is None
        assert runner.state["review_route"] is None
