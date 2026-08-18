"""
Endpoint bootstrap. Chỉ hai hàm chạm mạng (extract_voice / extract_brand) bị
mock — phần còn lại chạy thật.
"""
import json
import os

import pytest

os.environ["ENV"] = "dev"

from fastapi.testclient import TestClient  # noqa: E402

import api.routes.brands as brands_route  # noqa: E402
import src.knowledge.brand_manager as bm_mod  # noqa: E402
from api.main import app  # noqa: E402
from src.knowledge import brand_bootstrap as bb  # noqa: E402
from src.knowledge.brand_manager import BrandManager  # noqa: E402

from test_brand_bootstrap import a_brand, a_voice  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    brands = tmp_path / "brands"
    brands.mkdir()
    monkeypatch.setattr(bm_mod, "BRANDS_DIR", brands)
    # Route dùng một instance BrandManager tạo lúc import module
    monkeypatch.setattr(brands_route, "manager", BrandManager())
    brands_route.manager.create_brand("ca_phe_abc", "Cà Phê ABC")
    return TestClient(app), brands


def test_chang_1_tra_ve_draft_va_khong_ghi_gi(client, monkeypatch):
    c, brands = client
    monkeypatch.setattr(bb, "extract_voice", lambda samples: a_voice())

    truoc = (brands / "ca_phe_abc" / "tone_of_voice.md").read_text(encoding="utf-8")

    r = c.post("/api/brands/ca_phe_abc/bootstrap/voice", json={"samples": ["bài mẫu"]})
    assert r.status_code == 200, r.text

    data = r.json()
    paths = {f["path"] for f in data["files"]}
    assert paths == {"tone_of_voice.md", "content_framework.md"}
    assert data["voice_profile"]["tone"]["primary"] == "thân mật"

    sau = (brands / "ca_phe_abc" / "tone_of_voice.md").read_text(encoding="utf-8")
    assert truoc == sau, "chặng extract không được ghi file"


def test_chang_2_tra_ve_draft_kem_cho_chua_chac(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr(bb, "extract_brand", lambda documents: a_brand())

    r = c.post("/api/brands/ca_phe_abc/bootstrap/brand", json={"documents": ["hồ sơ"]})
    assert r.status_code == 200, r.text

    data = r.json()
    assert {f["path"] for f in data["files"]} == {
        "identity.md",
        "products/san_pham.md",
        "audience/khach_hang_chinh.md",
    }
    assert data["brand_meta"]["forbidden_claims"] == ["tốt nhất Việt Nam"]
    assert any("giao hàng" in n for n in data["notes"])


def test_apply_chi_ghi_thu_duoc_gui_len(client, monkeypatch):
    c, brands = client
    monkeypatch.setattr(bb, "extract_voice", lambda samples: a_voice())

    draft = c.post(
        "/api/brands/ca_phe_abc/bootstrap/voice", json={"samples": ["bài"]}
    ).json()
    chi_khung = [f for f in draft["files"] if f["path"] == "content_framework.md"]

    r = c.post(
        "/api/brands/ca_phe_abc/bootstrap/apply",
        json={"files": chi_khung, "voice_profile": draft["voice_profile"]},
    )
    assert r.status_code == 200, r.text
    assert set(r.json()["written"]) == {"content_framework.md", "voice_profile.json"}

    brand_dir = brands / "ca_phe_abc"
    assert (brand_dir / "content_framework.md").exists()
    assert "(Mô tả tone tại đây)" in (brand_dir / "tone_of_voice.md").read_text(encoding="utf-8")

    vp = json.loads((brand_dir / "voice_profile.json").read_text(encoding="utf-8"))
    assert vp["tone"]["primary"] == "thân mật"


def test_apply_rong_bi_tu_choi(client):
    c, _ = client
    r = c.post("/api/brands/ca_phe_abc/bootstrap/apply", json={"files": []})
    assert r.status_code == 400
    assert "Chưa chọn gì" in r.json()["detail"]["message"]


def test_tai_lieu_qua_dai_tra_413(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr(bb, "extract_voice", lambda samples: a_voice())

    r = c.post(
        "/api/brands/ca_phe_abc/bootstrap/voice",
        json={"samples": ["x" * (bb.MAX_INPUT_CHARS + 1)]},
    )
    assert r.status_code == 413
    assert "quá dài" in r.json()["detail"]["message"]


def test_brand_khong_ton_tai_tra_404(client):
    c, _ = client
    r = c.post("/api/brands/khong_co/bootstrap/voice", json={"samples": ["x"]})
    assert r.status_code == 404


def test_samples_rong_bi_validate_chan(client):
    c, _ = client
    r = c.post("/api/brands/ca_phe_abc/bootstrap/voice", json={"samples": []})
    assert r.status_code == 422


def test_path_traversal_qua_apply_bi_chan(client):
    """path trong draft đến từ client — phải bị chặn ở tầng đường dẫn."""
    c, _ = client
    r = c.post(
        "/api/brands/ca_phe_abc/bootstrap/apply",
        json={"files": [{"path": "../../../evil", "content": "xấu"}]},
    )
    assert r.status_code == 400, r.text
    assert "outputs" not in r.text.lower()
