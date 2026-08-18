"""
Test tích hợp qua HTTP cho A1 — lỗi nằm ở tầng route, không phải ở class cache,
nên test đơn vị trên key là chưa đủ.

Kịch bản đúng cái đã hỏng: user sửa chiến lược rồi duyệt. Nội dung PHẢI được
sinh lại từ chiến lược mới, không được lấy từ cache của chiến lược cũ.

Không có call API thật: mọi node LLM đều bị thay bằng hàm giả.
"""
import os

import pytest

os.environ["ENV"] = "dev"

from fastapi.testclient import TestClient  # noqa: E402

import api.cache as cache_mod  # noqa: E402
import api.pipeline_runner as pr  # noqa: E402
import api.routes.campaign as campaign_mod  # noqa: E402
from api.main import app  # noqa: E402
from src.models.content import CampaignContent, ContentPiece  # noqa: E402
from src.models.brief import Channel, Deliverable  # noqa: E402


@pytest.fixture
def calls():
    return {"strategist": 0, "architect": 0, "renderer": 0}


@pytest.fixture
def client(tmp_path, monkeypatch, calls, brief, master_message):
    """
    App với toàn bộ node LLM thay bằng hàm giả, cache và session ghi vào tmp.
    """
    monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(campaign_mod, "_SESSIONS_DIR", tmp_path / "sessions")
    campaign_mod.sessions._cache.clear()

    def fake_brief_parser(state):
        return {"brief": brief.model_copy(deep=True), "current_node": "brief_parser"}

    def fake_context_builder(state):
        return {
            "context_pack": {"mode": "generic", "brand_name": "", "loaded_docs": []},
            "current_node": "context_builder",
        }

    def fake_strategist(state):
        calls["strategist"] += 1
        fb = state.get("strategy_feedback")
        return {
            "strategy": f"Chiến lược bản {calls['strategist']}"
            + (f" (đã sửa theo: {fb})" if fb else ""),
            "current_node": "strategist",
        }

    def fake_architect(state):
        calls["architect"] += 1
        mm = master_message.model_copy(deep=True)
        # Ghi chiến lược đang thấy vào output để test kiểm được nó đọc bản nào
        mm.core_promise = f"dựa trên: {state['strategy']}"
        return {"master_message": mm, "current_node": "message_architect"}

    def fake_renderer(state):
        calls["renderer"] += 1
        piece = ContentPiece(
            channel=Channel.FACEBOOK,
            deliverable=Deliverable.POST,
            body=state["master_message"].core_promise,
            cta_text="Ghé quán",
            word_count=200,
        )
        return {
            "campaign_content": CampaignContent(
                pieces=[piece],
                master_message_summary=state["master_message"].core_promise,
            ),
            "warnings": [],
            "current_node": "channel_renderer",
        }

    monkeypatch.setattr(pr, "brief_parser_node", fake_brief_parser)
    monkeypatch.setattr(pr, "context_builder_node", fake_context_builder)
    monkeypatch.setattr(pr, "strategist_node", fake_strategist)
    monkeypatch.setattr(pr, "message_architect_node", fake_architect)
    monkeypatch.setattr(pr, "channel_renderer_node", fake_renderer)

    return TestClient(app)


INPUT = {"mode": "free_text", "raw_input": "Tạo campaign awareness cho cà phê rang mộc"}


def _start(client):
    r = client.post("/api/campaigns/start", json=INPUT)
    assert r.status_code == 200, r.text
    return r.json()["run_id"]


def test_sua_chien_luoc_thi_noi_dung_sinh_lai_tu_ban_moi(client, calls):
    """
    A1 — kịch bản trước đây bị bỏ qua âm thầm.

    Phải có một run sạch chạy trước để cache có dữ liệu, vì lỗi cũ là "lấy
    content của run trước cho chiến lược đã sửa của run này".
    """
    # Run 1: chạy thẳng, không sửa gì -> nạp cache cho raw_input này
    run1 = _start(client)
    client.post(f"/api/campaigns/{run1}/approve-brief", json=None)
    client.post(f"/api/campaigns/{run1}/review-strategy", json={"approved": True})
    architect_sau_run1 = calls["architect"]
    assert architect_sau_run1 == 1

    # Run 2: cùng raw_input, nhưng user yêu cầu SỬA chiến lược
    run2 = _start(client)
    client.post(f"/api/campaigns/{run2}/approve-brief", json=None)

    r = client.post(
        f"/api/campaigns/{run2}/review-strategy",
        json={"approved": False, "feedback_checks": ["tone"], "comment": "casual hơn"},
    )
    assert r.status_code == 200
    strategy_v2 = r.json()["strategy"]
    assert "đã sửa theo" in strategy_v2

    # Duyệt chiến lược đã sửa -> content PHẢI được sinh lại từ bản 2,
    # không được lấy content đã cache của run 1
    r = client.post(f"/api/campaigns/{run2}/review-strategy", json={"approved": True})
    assert r.status_code == 200
    data = r.json()

    assert calls["architect"] == architect_sau_run1 + 1, (
        "Content lấy từ cache nghĩa là chiến lược user vừa sửa bị bỏ qua"
    )
    assert data["master_message"]["core_promise"] == f"dựa trên: {strategy_v2}"
    assert "đã sửa theo" in data["content"]["pieces"][0]["body"]


def test_run_giong_nhau_van_dung_duoc_cache(client, calls):
    """Fix không được làm cache mất tác dụng hoàn toàn."""
    # Run 1: chạy thẳng, không sửa gì -> ghi cache
    run1 = _start(client)
    client.post(f"/api/campaigns/{run1}/approve-brief", json=None)
    client.post(f"/api/campaigns/{run1}/review-strategy", json={"approved": True})
    assert calls["strategist"] == 1
    assert calls["architect"] == 1

    # Run 2: cùng input, cùng brief, cùng chiến lược -> phải hit cache cả 2 chặng
    run2 = _start(client)
    client.post(f"/api/campaigns/{run2}/approve-brief", json=None)
    assert calls["strategist"] == 1, "Chiến lược phải lấy từ cache"

    r = client.post(f"/api/campaigns/{run2}/review-strategy", json={"approved": True})
    assert r.status_code == 200
    assert calls["architect"] == 1, "Nội dung phải lấy từ cache"
    assert r.json()["content"]["pieces"]


def test_sua_brief_khong_lam_nhiem_cache_cua_brief_goc(client, calls):
    """A2: chiến lược của brief đã sửa không được ghi đè key của brief gốc."""
    # Run 1: sửa brief rồi duyệt -> chiến lược bản 1 thuộc về brief ĐÃ SỬA
    run1 = _start(client)
    r = client.post(
        f"/api/campaigns/{run1}/approve-brief",
        json={"product": "Cà phê phin truyền thống"},
    )
    assert r.status_code == 200
    assert calls["strategist"] == 1

    # Run 2: cùng raw_input nhưng KHÔNG sửa brief -> không được nhận chiến lược
    # của run 1, phải gọi strategist lần nữa
    run2 = _start(client)
    r = client.post(f"/api/campaigns/{run2}/approve-brief", json=None)
    assert r.status_code == 200
    assert calls["strategist"] == 2, (
        "Brief khác nhau mà dùng chung cache là lỗi A2"
    )
