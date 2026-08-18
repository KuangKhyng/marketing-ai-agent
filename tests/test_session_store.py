"""
Kèm G5 — state.pkl phải có version.

Schema của ReviewResult vừa đổi (thêm review_unavailable, rule_violations).
File pickle cũ khôi phục ra object thiếu field sẽ vỡ ở chỗ khác, khó truy.
Nên file sai version phải bị coi như hết hạn.
"""
import pickle

from api.routes.campaign import _STATE_VERSION, SessionStore
from api.pipeline_runner import PipelineRunner


def _store(tmp_path, monkeypatch):
    import api.routes.campaign as campaign_mod

    monkeypatch.setattr(campaign_mod, "_SESSIONS_DIR", tmp_path)
    return SessionStore(ttl_minutes=120)


def test_luu_roi_doc_lai_duoc(tmp_path, monkeypatch):
    store = _store(tmp_path, monkeypatch)
    runner = PipelineRunner()
    runner.state = {"raw_input": "abc", "warnings": []}

    store.set("run00001", runner)
    store._cache.clear()  # giả lập server restart

    lay_lai = store.get("run00001")
    assert lay_lai is not None
    assert lay_lai.state["raw_input"] == "abc"


def test_file_khong_co_version_bi_bo(tmp_path, monkeypatch):
    """Format cũ: pickle thẳng state dict, không bọc version."""
    store = _store(tmp_path, monkeypatch)
    path = tmp_path / "run00002" / "state.pkl"
    path.parent.mkdir(parents=True)
    with open(path, "wb") as f:
        pickle.dump({"raw_input": "state format cũ"}, f)

    assert store.get("run00002") is None
    assert not path.exists(), "File cũ phải bị xoá luôn cho khỏi thử lại mỗi lần"


def test_file_sai_version_bi_bo(tmp_path, monkeypatch):
    store = _store(tmp_path, monkeypatch)
    path = tmp_path / "run00003" / "state.pkl"
    path.parent.mkdir(parents=True)
    with open(path, "wb") as f:
        pickle.dump({"version": _STATE_VERSION + 1, "state": {"raw_input": "x"}}, f)

    assert store.get("run00003") is None


def test_file_hong_khong_lam_crash(tmp_path, monkeypatch):
    store = _store(tmp_path, monkeypatch)
    path = tmp_path / "run00004" / "state.pkl"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"khong phai pickle")

    assert store.get("run00004") is None
