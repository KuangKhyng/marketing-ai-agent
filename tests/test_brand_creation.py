"""
Tạo brand TỪ tài liệu.

Điểm phải canh:
  - preview không được tạo gì
  - điểm hoàn thiện hứa trước phải khớp điểm thật sau khi tạo
  - mã brand không đổi được sau khi tạo, nên phải chặn trùng và chặn sai format
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
    monkeypatch.setattr(brands_route, "manager", BrandManager())
    return TestClient(app), brands


@pytest.fixture
def mocked_extract(monkeypatch):
    """Hai hàm duy nhất chạm mạng."""
    monkeypatch.setattr(
        bb,
        "extract_for_creation",
        lambda samples, documents: (
            a_voice() if samples else None,
            a_brand(brand_name="Tử Vi Online", short_description="Dịch vụ xem tử vi online")
            if documents
            else None,
            bb.ExtractUsage(input_tokens=4000, output_tokens=1200, cost_estimate=0.03),
        ),
    )


# === slug ===


class TestSlug:
    @pytest.mark.parametrize(
        "ten,mong_doi",
        [
            ("Tử Vi Online", "tu_vi_online"),
            ("Cà Phê ABC", "ca_phe_abc"),
            ("Đông Y Đường", "dong_y_duong"),
            ("Học Tiếng Anh 24/7", "hoc_tieng_anh_24_7"),
            ("", "brand_moi"),
            ("   ", "brand_moi"),
            ("!!!", "brand_moi"),
        ],
    )
    def test_bo_dau_tieng_viet(self, ten, mong_doi):
        assert bb.slugify_brand_id(ten) == mong_doi

    def test_luon_hop_le_voi_validate_id(self):
        from src.utils.paths import validate_id

        for ten in ["Tử Vi Online", "A" * 200, "!@#$%^", "Đ Đ Đ", "café ☕ shop"]:
            validate_id(bb.slugify_brand_id(ten), "brand_id")  # không raise là đạt


# === preview ===


class TestPreview:
    def test_khong_co_tai_lieu_thi_tu_choi(self, client):
        c, _ = client
        r = c.post("/api/brands/bootstrap/preview", json={"samples": [], "documents": []})
        assert r.status_code == 400
        assert "ít nhất một" in r.json()["detail"]["message"]

    def test_khong_tao_gi_ca(self, client, mocked_extract):
        c, brands = client
        r = c.post("/api/brands/bootstrap/preview", json={"documents": ["hồ sơ"]})
        assert r.status_code == 200, r.text
        assert list(brands.iterdir()) == [], "preview không được tạo thư mục brand nào"

    def test_de_xuat_ten_va_ma_tu_tai_lieu(self, client, mocked_extract):
        c, _ = client
        r = c.post("/api/brands/bootstrap/preview", json={"documents": ["hồ sơ"]})

        identity = r.json()["identity"]
        assert identity["name"] == "Tử Vi Online"
        assert identity["suggested_id"] == "tu_vi_online"
        assert identity["description"] == "Dịch vụ xem tử vi online"
        assert identity["id_taken"] is False

    def test_bao_khi_ma_da_bi_dung(self, client, mocked_extract):
        c, _ = client
        brands_route.manager.create_brand("tu_vi_online", "Tử Vi Online")

        r = c.post("/api/brands/bootstrap/preview", json={"documents": ["hồ sơ"]})
        assert r.json()["identity"]["id_taken"] is True

    def test_ten_nguoi_dung_go_thang_hon_tai_lieu(self, client, mocked_extract):
        c, _ = client
        r = c.post(
            "/api/brands/bootstrap/preview",
            json={"documents": ["hồ sơ"], "name_hint": "Tử Vi Cô Ba"},
        )
        assert r.json()["identity"]["name"] == "Tử Vi Cô Ba"
        assert r.json()["identity"]["suggested_id"] == "tu_vi_co_ba"

    def test_gop_ca_hai_loai_tai_lieu(self, client, mocked_extract):
        c, _ = client
        r = c.post(
            "/api/brands/bootstrap/preview",
            json={"samples": ["bài cũ"], "documents": ["hồ sơ"]},
        )
        paths = {f["path"] for f in r.json()["draft"]["files"]}
        assert paths == {
            "tone_of_voice.md",
            "content_framework.md",
            "identity.md",
            "products/san_pham.md",
            "audience/khach_hang_chinh.md",
        }
        assert r.json()["draft"]["voice_profile"] is not None

    def test_chi_co_bai_dang_van_dung_duoc(self, client, mocked_extract):
        c, _ = client
        r = c.post("/api/brands/bootstrap/preview", json={"samples": ["bài cũ"]})
        paths = {f["path"] for f in r.json()["draft"]["files"]}
        assert paths == {"tone_of_voice.md", "content_framework.md"}
        assert r.json()["completeness"]["score"] == 25, "mới có giọng, chưa có identity"

    def test_route_khong_bi_brand_id_che(self, client, mocked_extract):
        """'bootstrap' không được khớp vào {brand_id}."""
        c, _ = client
        r = c.post("/api/brands/bootstrap/preview", json={"documents": ["x"]})
        assert r.status_code == 200, f"route bị che: {r.status_code} {r.text[:200]}"


# === create ===


class TestCreate:
    def _preview(self, c):
        return c.post(
            "/api/brands/bootstrap/preview",
            json={"samples": ["bài cũ"], "documents": ["hồ sơ"]},
        ).json()

    def test_tao_brand_day_du_tu_draft(self, client, mocked_extract):
        c, brands = client
        p = self._preview(c)

        r = c.post(
            "/api/brands/bootstrap/create",
            json={
                "id": p["identity"]["suggested_id"],
                "name": p["identity"]["name"],
                "description": p["identity"]["description"],
                "files": p["draft"]["files"],
                "voice_profile": p["draft"]["voice_profile"],
                "brand_meta": p["draft"]["brand_meta"],
            },
        )
        assert r.status_code == 200, r.text

        brand_dir = brands / "tu_vi_online"
        assert (brand_dir / "identity.md").exists()
        assert (brand_dir / "content_framework.md").exists()
        assert (brand_dir / "products" / "san_pham.md").exists()

        meta = json.loads((brand_dir / "brand.json").read_text(encoding="utf-8"))
        assert meta["name"] == "Tử Vi Online"
        assert meta["description"] == "Dịch vụ xem tử vi online"
        assert meta["forbidden_claims"] == ["tốt nhất Việt Nam"]

        vp = json.loads((brand_dir / "voice_profile.json").read_text(encoding="utf-8"))
        assert vp["profile_id"] == "tu_vi_online", "profile_id phải theo mã brand thật"
        assert vp["tone"]["primary"] == "thân mật"

    def test_diem_hua_truoc_khop_diem_that_sau(self, client, mocked_extract):
        """Xem trước mà nói dối thì thà đừng hiện."""
        c, _ = client
        p = self._preview(c)
        hua = p["completeness"]["score"]

        c.post(
            "/api/brands/bootstrap/create",
            json={
                "id": p["identity"]["suggested_id"],
                "name": p["identity"]["name"],
                "files": p["draft"]["files"],
            },
        )
        that = c.get("/api/brands/tu_vi_online").json()["completeness"]["score"]

        assert hua == that == 100

    def test_bo_bot_file_thi_diem_thap_hon(self, client, mocked_extract):
        c, _ = client
        p = self._preview(c)
        khong_lay_audience = [
            f for f in p["draft"]["files"] if not f["path"].startswith("audience/")
        ]

        c.post(
            "/api/brands/bootstrap/create",
            json={
                "id": "tu_vi_online",
                "name": "Tử Vi Online",
                "files": khong_lay_audience,
            },
        )
        checks = c.get("/api/brands/tu_vi_online").json()["completeness"]
        assert checks["score"] == 75
        assert checks["checks"]["audience"] is False

    def test_luu_tai_lieu_goc(self, client, mocked_extract):
        c, brands = client
        p = self._preview(c)

        c.post(
            "/api/brands/bootstrap/create",
            json={
                "id": "tu_vi_online",
                "name": "Tử Vi Online",
                "files": p["draft"]["files"],
                "sources": {"bai_dang_1": "nội dung bài cũ", "tai_lieu_1": "hồ sơ brand"},
            },
        )

        sources = brands / "tu_vi_online" / "_sources"
        assert (sources / "bai_dang_1.txt").read_text(encoding="utf-8") == "nội dung bài cũ"

        # Không được lẫn vào tab Tài liệu, cũng không được vào context của pipeline
        docs = {d["path"] for d in c.get("/api/brands/tu_vi_online").json()["documents"]}
        assert not any(d.startswith("_sources") for d in docs)

    def test_ma_trung_bi_tu_choi(self, client, mocked_extract):
        c, _ = client
        brands_route.manager.create_brand("tu_vi_online", "Cái đã có")

        r = c.post(
            "/api/brands/bootstrap/create",
            json={"id": "tu_vi_online", "name": "Tử Vi Online", "files": []},
        )
        assert r.status_code == 409

    def test_ma_sai_format_bi_chan(self, client):
        c, _ = client
        r = c.post(
            "/api/brands/bootstrap/create",
            json={"id": "../../etc", "name": "Xấu", "files": []},
        )
        assert r.status_code == 400
        assert "outputs" not in r.text.lower()

    def test_thieu_ten_bi_tu_choi(self, client):
        c, _ = client
        r = c.post(
            "/api/brands/bootstrap/create",
            json={"id": "brand_moi", "name": "   ", "files": []},
        )
        assert r.status_code == 400
