"""
R1 — một lượt LLM lỗi không được giết cả phiên.

Mọi node đều mở đầu bằng `if state.get("error"): return`, mà PipelineRunner
sống trong SessionStore và bị mutate tại chỗ. Không xoá lỗi trước lượt mới thì:

    strategy -> Anthropic timeout -> state["error"] = "..."
    -> user bấm Retry -> strategist thấy error -> return ngay -> phiên chết hẳn

Đây là bug vòng đời, không phải edge case: chỉ cần một lần timeout.
"""
import os

import pytest

os.environ["ENV"] = "dev"

from fastapi.testclient import TestClient  # noqa: E402

import api.pipeline_runner as pr  # noqa: E402
import api.routes.campaign as campaign_mod  # noqa: E402
import api.cache as cache_mod  # noqa: E402
from api.main import app  # noqa: E402
from api.pipeline_runner import PipelineRunner  # noqa: E402
from src.models.content import CampaignContent, ContentPiece  # noqa: E402
from src.models.brief import Channel, Deliverable  # noqa: E402


@pytest.fixture
def nodes(monkeypatch, brief, master_message):
    """
    Node giả điều khiển được: bảo nó hỏng lượt nào thì hỏng lượt đó.

    `hong` là tập tên node sẽ hỏng ở lượt gọi TIẾP THEO.
    """
    dem = {"strategist": 0, "message_architect": 0, "channel_renderer": 0, "reviewer": 0}
    hong = set()

    def fake_parse(state):
        return {"brief": brief.model_copy(deep=True), "current_node": "brief_parser"}

    def fake_context(state):
        return {"context_pack": {"mode": "generic"}, "current_node": "context_builder"}

    def lam_node(ten, ket_qua):
        def node(state):
            if state.get("error"):
                return {"current_node": ten}
            dem[ten] += 1
            if ten in hong:
                hong.discard(ten)
                return {"error": f"{ten}: Anthropic timeout", "current_node": ten}
            return {**ket_qua(state), "current_node": ten}

        return node

    piece = ContentPiece(
        channel=Channel.FACEBOOK, deliverable=Deliverable.POST,
        body="Nội dung " * 60, cta_text="Ghé quán", word_count=120,
    )

    monkeypatch.setattr(pr, "brief_parser_node", fake_parse)
    monkeypatch.setattr(pr, "context_builder_node", fake_context)
    monkeypatch.setattr(pr, "strategist_node", lam_node(
        "strategist", lambda s: {"strategy": f"Chiến lược lượt {dem['strategist']}"}))
    monkeypatch.setattr(pr, "message_architect_node", lam_node(
        "message_architect", lambda s: {"master_message": master_message.model_copy(deep=True)}))
    monkeypatch.setattr(pr, "channel_renderer_node", lam_node(
        "channel_renderer", lambda s: {
            "campaign_content": CampaignContent(pieces=[piece], master_message_summary="x"),
            "warnings": [],
        }))

    return dem, hong


# === Ở tầng runner ===


class TestRunner:
    def test_chay_lai_duoc_sau_khi_loi(self, nodes):
        dem, hong = nodes
        runner = PipelineRunner()
        runner.phase_1_parse("cà phê")

        hong.add("strategist")
        state = runner.phase_2_strategy()
        assert state["error"], "lượt đầu phải hỏng"

        # Người dùng bấm thử lại
        state = runner.phase_2_strategy()

        assert not state.get("error"), "lượt sau phải chạy được"
        assert state["strategy"] == "Chiến lược lượt 2"
        assert dem["strategist"] == 2, "node phải thật sự chạy lại, không phải return ngay"

    def test_giu_lai_loi_cu_de_truy(self, nodes):
        dem, hong = nodes
        runner = PipelineRunner()
        runner.phase_1_parse("cà phê")

        hong.add("strategist")
        runner.phase_2_strategy()
        runner.phase_2_strategy()

        assert runner.state["last_error"]["message"].startswith("strategist:")
        assert runner.state["attempt"] == 2

    def test_loi_o_phase_truoc_khong_chan_phase_sau(self, nodes):
        """Sửa chiến lược hỏng rồi thì vẫn duyệt tiếp được sau khi chạy lại."""
        dem, hong = nodes
        runner = PipelineRunner()
        runner.phase_1_parse("cà phê")
        runner.phase_2_strategy()

        hong.add("message_architect")
        state = runner.phase_3_content()
        assert state["error"]

        state = runner.phase_3_content()
        assert not state.get("error")
        assert state["campaign_content"].pieces


# === Ở tầng HTTP ===


@pytest.fixture
def client(tmp_path, monkeypatch, nodes):
    monkeypatch.setattr(campaign_mod, "_SESSIONS_DIR", tmp_path / "sessions")
    monkeypatch.setattr(cache_mod, "_CACHE_DIR", tmp_path / "cache")
    campaign_mod.sessions._cache.clear()
    return TestClient(app), nodes


def _start(c):
    r = c.post("/api/campaigns/start", json={"mode": "free_text", "raw_input": "cà phê rang mộc"})
    assert r.status_code == 200, r.text
    return r.json()["run_id"]


class TestQuaHttp:
    def test_phien_khong_chet_sau_mot_lan_timeout(self, client):
        c, (dem, hong) = client
        run_id = _start(c)

        hong.add("strategist")
        r = c.post(f"/api/campaigns/{run_id}/approve-brief", json=None)
        assert r.status_code == 500

        # Bấm thử lại — trước đây chỗ này trả 500 mãi mãi
        r = c.post(f"/api/campaigns/{run_id}/approve-brief", json=None)
        assert r.status_code == 200, "phiên bị kẹt vĩnh viễn sau một lần LLM lỗi"
        assert r.json()["strategy"]

    def test_sua_chien_luoc_hong_thi_phai_bao_hong(self, client):
        """Trả 200 kèm chiến lược cũ nguyên si là nói dối rằng đã sửa xong."""
        c, (dem, hong) = client
        run_id = _start(c)
        c.post(f"/api/campaigns/{run_id}/approve-brief", json=None)

        hong.add("strategist")
        r = c.post(
            f"/api/campaigns/{run_id}/review-strategy",
            json={"approved": False, "comment": "casual hơn"},
        )
        assert r.status_code == 500, r.text

        # và vẫn sửa lại được sau đó
        r = c.post(
            f"/api/campaigns/{run_id}/review-strategy",
            json={"approved": False, "comment": "casual hơn"},
        )
        assert r.status_code == 200
        assert "lượt 3" in r.json()["strategy"]

    def test_sua_noi_dung_hong_thi_phai_bao_hong(self, client):
        c, (dem, hong) = client
        run_id = _start(c)
        c.post(f"/api/campaigns/{run_id}/approve-brief", json=None)
        c.post(f"/api/campaigns/{run_id}/review-strategy", json={"approved": True})

        hong.add("channel_renderer")
        r = c.post(
            f"/api/campaigns/{run_id}/review-content",
            json={"approved": False, "piece_feedbacks": [
                {"piece_index": 0, "approved": False, "comment": "viết lại"}]},
        )
        assert r.status_code == 500, r.text


# === R2: hai tab không được chạy song song cùng một run ===


class TestKhoaTheoRun:
    def test_dang_chay_thi_request_thu_hai_bi_tu_choi(self, client):
        """
        Trước đây SessionStore chỉ khoá thao tác trên dict; sau khi trả runner
        ra ngoài thì route mutate state không còn khoá nào. Hai tab cùng bấm =
        hai lượt gọi Claude cho cùng một việc, rồi last-write-wins.
        """
        import threading

        c, (dem, hong) = client
        run_id = _start(c)

        dang_chay = threading.Event()
        cho_tha = threading.Event()
        goc = campaign_mod.sessions.get(run_id).phase_2_strategy

        def cham(*a, **kw):
            dang_chay.set()
            cho_tha.wait(timeout=5)
            return goc(*a, **kw)

        campaign_mod.sessions.get(run_id).phase_2_strategy = cham

        ket_qua = {}
        t = threading.Thread(
            target=lambda: ket_qua.update(
                dau=c.post(f"/api/campaigns/{run_id}/approve-brief", json=None).status_code
            )
        )
        t.start()
        assert dang_chay.wait(timeout=5), "request đầu chưa kịp vào phase"

        # Tab thứ hai bấm trong lúc tab đầu đang gọi Claude
        r2 = c.post(f"/api/campaigns/{run_id}/approve-brief", json=None)

        cho_tha.set()
        t.join(timeout=10)

        assert r2.status_code == 409, "phải từ chối chứ không chạy song song"
        assert "đang chạy" in r2.json()["detail"]["message"]
        assert ket_qua["dau"] == 200, "request đầu vẫn phải chạy xong bình thường"
        assert dem["strategist"] == 1, "chỉ được gọi LLM đúng một lần"

    def test_chay_xong_thi_tha_khoa(self, client):
        c, (dem, hong) = client
        run_id = _start(c)

        assert c.post(f"/api/campaigns/{run_id}/approve-brief", json=None).status_code == 200
        assert c.post(f"/api/campaigns/{run_id}/approve-brief", json=None).status_code == 200

    def test_loi_cung_phai_tha_khoa(self, client):
        """Phase hỏng mà giữ khoá thì run kẹt vĩnh viễn — đúng bug vừa sửa ở R1."""
        c, (dem, hong) = client
        run_id = _start(c)

        hong.add("strategist")
        assert c.post(f"/api/campaigns/{run_id}/approve-brief", json=None).status_code == 500
        assert c.post(f"/api/campaigns/{run_id}/approve-brief", json=None).status_code == 200
