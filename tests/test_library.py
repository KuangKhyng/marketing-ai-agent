import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import library
from api.routes.campaign import run_locks
from api.schemas import PipelineStatus


@pytest.fixture
def setup_library(tmp_path, monkeypatch, content):
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.delenv("APP_API_KEY", raising=False)
    monkeypatch.setattr(library, "LIBRARY_DIR", tmp_path / "library")
    state = PipelineStatus(run_id="savedrun", phase="content_review",
                           content=content.model_dump(mode="json"),
                           warnings=["Chưa có tài liệu sản phẩm"])
    monkeypatch.setattr(library, "get_run", lambda run_id: state)
    return TestClient(app), state


def save(client, **values):
    return client.post("/api/library", json={"run_id": "savedrun", "title": "Phương án A", **values})


def test_snapshot_survives_session_expiry_and_is_immutable(setup_library, monkeypatch):
    client, state = setup_library
    saved = save(client).json()
    assert saved["campaign"]["warnings"] == state.warnings
    state.content["pieces"][0]["body"] = "New content"
    monkeypatch.setattr(library, "get_run", lambda _: pytest.fail("Must not read session"))
    result = client.get(f'/api/library/{saved["id"]}')
    assert result.status_code == 200
    assert result.json() == saved
    download = client.get(f'/api/library/{saved["id"]}/download')
    assert download.json() == saved
    assert "attachment" in download.headers["content-disposition"]


def test_retries_do_not_duplicate_but_new_content_creates_version(setup_library):
    client, state = setup_library
    first = save(client).json()
    assert save(client).json() == first
    state.content["pieces"][0]["body"] = "Updated content"
    second = save(client).json()
    assert second["id"] != first["id"]
    assert len(client.get("/api/library").json()) == 2


def test_refuses_busy_run_and_empty_content(setup_library):
    client, state = setup_library
    with run_locks.acquire("savedrun"):
        assert save(client).status_code == 409
    state.content = None
    assert save(client).status_code == 409


def test_validation_and_missing_snapshot(setup_library):
    client, _ = setup_library
    assert save(client, title="   ").status_code == 422
    assert save(client, title="x" * 161).status_code == 422
    assert save(client, run_id="../escape").status_code == 400
    assert client.get("/api/library/missing").status_code == 404


def test_write_failure_does_not_report_success(setup_library, monkeypatch):
    client, _ = setup_library
    def fail(*args):
        raise OSError("disk full")
    monkeypatch.setattr(library, "atomic_write_text", fail)
    assert save(client).status_code == 503
    assert client.get("/api/library").json() == []


def test_list_skips_corrupt_files(setup_library):
    client, _ = setup_library
    saved = save(client).json()
    (library.LIBRARY_DIR / "broken.json").write_text("{", encoding="utf-8")
    assert [item["id"] for item in client.get("/api/library").json()] == [saved["id"]]
    assert client.get("/api/library/broken").status_code == 503


def test_library_requires_authentication(setup_library, monkeypatch):
    client, _ = setup_library
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("APP_API_KEY", "test-library-key")
    assert client.get("/api/library").status_code == 401
    assert save(client).status_code == 401
    assert client.get("/api/library/missing").status_code == 401
    assert client.get("/api/library/missing/download").status_code == 401
    assert client.get("/api/library", headers={"X-API-Key": "test-library-key"}).status_code == 200
