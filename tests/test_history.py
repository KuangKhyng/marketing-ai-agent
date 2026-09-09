import json
from api.routes.campaign import list_campaigns


def test_history_skips_corrupt_traces_and_sorts_by_timestamp(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.settings.PROJECT_ROOT", tmp_path)
    for name, payload in [("z", {"started_at": "2026-01-01"}), ("a", {"started_at": "2026-02-01"}), ("bad", None)]:
        folder = tmp_path / "outputs" / name
        folder.mkdir(parents=True)
        (folder / "trace.json").write_text(json.dumps(payload) if payload else "{broken", encoding="utf-8")
    assert [run["run_id"] for run in list_campaigns()] == ["a", "z"]
