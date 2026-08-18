"""
G5 — B3: mở lại một run đang dở.

Gồm cả cái bẫy dễ vỡ nhất khi thêm GET /{run_id}: nếu khai báo trước
/history thì "history" khớp vào {run_id} và endpoint kia thành 404.
"""
import os

import pytest

os.environ["ENV"] = "dev"  # tắt auth, phải set trước khi gọi endpoint

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from api.pipeline_runner import PipelineRunner  # noqa: E402
from api.routes.campaign import _infer_phase, sessions  # noqa: E402
from src.models.review import DimensionScore, ReviewDimension, ReviewResult  # noqa: E402
from src.models.trace import RunTrace  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def run_id(brief, content, master_message):
    """Nhét thẳng vào cache in-memory để test không ghi ra outputs/."""
    rid = "testrun1"
    runner = PipelineRunner()
    runner.state = {
        "raw_input": "cà phê rang mộc",
        "brand_id": None,
        "brief": brief,
        "strategy": "Chiến lược bản 1",
        "master_message": master_message,
        "campaign_content": content,
        "review_result": None,
        "revision_count": 0,
        "warnings": ["tiktok/short_video_script không tạo được"],
        "trace": RunTrace(),
    }
    sessions._cache[rid] = runner
    yield rid
    sessions._cache.pop(rid, None)


# === bẫy route ordering ===


def test_history_khong_bi_route_run_id_che(client):
    """GET /history phải là /history, không phải run_id tên 'history'."""
    r = client.get("/api/campaigns/history")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# === GET /{run_id} ===


def test_doc_lai_run_dang_do(client, run_id):
    r = client.get(f"/api/campaigns/{run_id}")
    assert r.status_code == 200

    data = r.json()
    assert data["run_id"] == run_id
    assert data["phase"] == "content_review"
    assert data["strategy"] == "Chiến lược bản 1"
    assert data["content"]["pieces"]
    assert data["warnings"] == ["tiktok/short_video_script không tạo được"]


def test_run_khong_ton_tai_tra_404(client):
    r = client.get("/api/campaigns/khongcothat")
    assert r.status_code == 404
    assert "detail" in r.json()


def test_run_id_sai_format_tra_400(client):
    """InvalidPathError phải thành 400, không phải 500 và không lộ path server."""
    r = client.get("/api/campaigns/..%2F..%2Fetc")
    assert r.status_code in (400, 404)
    assert "outputs" not in r.text.lower()


# === suy ra bước đang dở ===


class TestInferPhase:
    def test_chua_co_gi(self):
        assert _infer_phase({}) == "input"

    def test_co_brief(self, brief):
        assert _infer_phase({"brief": brief}) == "brief_review"

    def test_co_strategy(self, brief):
        assert _infer_phase({"brief": brief, "strategy": "x"}) == "strategy_review"

    def test_co_content(self, brief, content):
        state = {"brief": brief, "strategy": "x", "campaign_content": content}
        assert _infer_phase(state) == "content_review"

    def test_co_review_result(self, brief, content):
        result = ReviewResult(
            overall_passed=True,
            dimension_scores=[
                DimensionScore(dimension=d, score=0.9, passed=True, feedback="ok")
                for d in ReviewDimension
            ],
        )
        state = {"brief": brief, "campaign_content": content, "review_result": result}
        assert _infer_phase(state) == "final_review"

    def test_da_ban_giao(self, brief, content):
        trace = RunTrace()
        trace.final_status = "completed"
        result = ReviewResult(overall_passed=True, dimension_scores=[])
        state = {
            "brief": brief,
            "campaign_content": content,
            "review_result": result,
            "trace": trace,
        }
        assert _infer_phase(state) == "completed"
