"""
Hai thứ vừa thêm: chặn đốt tiền, và nhân bản brand.

Phần chi phí là chỗ dễ sai nhất vì nó vô hình — không ai nhận ra mình vừa gọi
API hai lần cho cùng một tài liệu cho tới khi nhìn hoá đơn.
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
from src.knowledge.brand_manager import BrandExistsError, BrandManager  # noqa: E402

from test_brand_bootstrap import a_voice  # noqa: E402


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    d = tmp_path / "bootstrap_cache"
    monkeypatch.setattr(bb, "_cache_dir", lambda: d)
    return d


@pytest.fixture
def dem_goi(monkeypatch):
    """Thay LLM bằng bản đếm số lần gọi. Không có mạng ở đây."""
    dem = {"n": 0}

    class FakeStructured:
        def invoke(self, messages, config=None):
            dem["n"] += 1
            return a_voice()

    class FakeLLM:
        def with_structured_output(self, schema):
            return FakeStructured()

    monkeypatch.setattr(bb, "_build_llm", lambda: FakeLLM())
    monkeypatch.setattr(bb, "_model_name", lambda: "claude-sonnet-4-6")
    return dem


# === Cache: đọc lại đúng tài liệu cũ thì không trả tiền lần nữa ===


class TestCache:
    def test_doc_lai_cung_tai_lieu_khong_goi_api(self, cache_dir, dem_goi):
        bai = ["bài số một", "bài số hai"]

        _, usage1 = bb.extract_voice(bai)
        _, usage2 = bb.extract_voice(bai)

        assert dem_goi["n"] == 1, "lần hai phải lấy từ cache"
        assert usage1.cached is False and usage1.cost_estimate > 0
        assert usage2.cached is True and usage2.cost_estimate == 0

    def test_doi_tai_lieu_thi_doc_lai(self, cache_dir, dem_goi):
        bb.extract_voice(["bài số một"])
        bb.extract_voice(["bài số một", "bài thêm"])
        assert dem_goi["n"] == 2

    def test_khoang_trang_thua_khong_lam_miss_cache(self, cache_dir, dem_goi):
        bb.extract_voice(["bài số một"])
        bb.extract_voice(["  bài số một  "])
        assert dem_goi["n"] == 1

    def test_sua_prompt_thi_ket_qua_cu_het_gia_tri(self, cache_dir, dem_goi, monkeypatch):
        bb.extract_voice(["bài"])
        monkeypatch.setattr(bb, "_prompt_text", lambda f: "PROMPT ĐÃ SỬA")
        bb.extract_voice(["bài"])
        assert dem_goi["n"] == 2, "prompt nằm trong khoá cache"

    def test_cache_hong_khong_lam_crash(self, cache_dir, dem_goi):
        bb.extract_voice(["bài"])
        for f in cache_dir.glob("*.json"):
            f.write_text("không phải json", encoding="utf-8")

        _, usage = bb.extract_voice(["bài"])
        assert usage.cached is False
        assert dem_goi["n"] == 2


# === Ước tính trước khi gọi ===


class TestEstimate:
    def test_khong_goi_api(self, cache_dir, dem_goi):
        est = bb.estimate_cost_for(["bài dài " * 500], [])
        assert dem_goi["n"] == 0, "ước tính mà gọi API thì vô nghĩa"
        assert est.estimated_cost > 0
        assert est.input_chars > 0

    def test_tai_lieu_dai_hon_thi_dat_hon(self, cache_dir, dem_goi):
        it = bb.estimate_cost_for(["ngắn"], [])
        nhieu = bb.estimate_cost_for(["dài " * 2000], [])
        assert nhieu.estimated_cost > it.estimated_cost

    def test_da_co_cache_thi_bao_khong_ton_gi(self, cache_dir, dem_goi):
        bai = ["bài đã đọc rồi"]
        assert bb.estimate_cost_for(bai, []).cached is False

        bb.extract_voice(bai)

        est = bb.estimate_cost_for(bai, [])
        assert est.cached is True
        assert est.estimated_cost == 0


# === Endpoint ===


@pytest.fixture
def client(tmp_path, monkeypatch):
    brands = tmp_path / "brands"
    brands.mkdir()
    monkeypatch.setattr(bm_mod, "BRANDS_DIR", brands)
    monkeypatch.setattr(brands_route, "manager", BrandManager())
    return TestClient(app), brands


def test_endpoint_estimate_khong_goi_api(client, cache_dir, dem_goi):
    c, _ = client
    r = c.post("/api/brands/bootstrap/estimate", json={"documents": ["hồ sơ dài " * 100]})

    assert r.status_code == 200, r.text
    assert dem_goi["n"] == 0
    assert r.json()["estimated_cost"] > 0
    assert r.json()["model"] == "claude-sonnet-4-6"


def test_draft_tra_ve_chi_phi_that(client, cache_dir, dem_goi, monkeypatch):
    c, _ = client
    brands_route.manager.create_brand("ca_phe_abc", "Cà Phê ABC")

    r = c.post("/api/brands/ca_phe_abc/bootstrap/voice", json={"samples": ["bài"]})
    usage = r.json()["usage"]

    assert usage["cached"] is False
    assert usage["cost_estimate"] > 0

    # Lần hai: cùng tài liệu, phải free
    r2 = c.post("/api/brands/ca_phe_abc/bootstrap/voice", json={"samples": ["bài"]})
    assert r2.json()["usage"]["cached"] is True
    assert r2.json()["usage"]["cost_estimate"] == 0
    assert dem_goi["n"] == 1


# === Nhân bản brand ===


class TestClone:
    @pytest.fixture
    def nguon(self, client):
        c, brands = client
        m = brands_route.manager
        m.create_brand("tu_vi_online", "Tử Vi Online", "Dịch vụ xem tử vi")
        m.save_document("tu_vi_online", "identity.md", "# Tử Vi Online\n\nXem tử vi từ 2015.")
        m.save_document("tu_vi_online", "tone_of_voice.md", "# Giọng\n\nNhẹ nhàng, không hù doạ.")
        m.save_document("tu_vi_online", "products/goi_xem.md", "# Gói xem lá số\n\n500k")
        m.save_document("tu_vi_online", "audience/khach.md", "# Khách\n\nGen Z quan tâm tâm linh")
        m.update_brand_meta("tu_vi_online", {"forbidden_claims": ["cải mệnh đổi vận"]})
        m.save_source("tu_vi_online", "bai_goc", "tài liệu gốc của brand cũ")
        return c, brands

    def test_chep_khung_nhung_bo_san_pham(self, nguon):
        c, brands = nguon
        r = c.post(
            "/api/brands/clone",
            json={"source_id": "tu_vi_online", "id": "phong_thuy_online", "name": "Phong Thuỷ Online"},
        )
        assert r.status_code == 200, r.text

        moi = brands / "phong_thuy_online"
        assert "Xem tử vi từ 2015" in (moi / "identity.md").read_text(encoding="utf-8")
        assert (moi / "tone_of_voice.md").exists()
        assert (moi / "audience" / "khach.md").exists()

        assert not (moi / "products" / "goi_xem.md").exists(), (
            "mặc định phải bỏ sản phẩm — nhân bản là để làm brand khác sản phẩm"
        )
        assert (moi / "products").is_dir(), "thư mục vẫn phải có để thêm sản phẩm mới"

    def test_giu_san_pham_khi_duoc_yeu_cau(self, nguon):
        c, brands = nguon
        c.post(
            "/api/brands/clone",
            json={
                "source_id": "tu_vi_online",
                "id": "tu_vi_v2",
                "name": "Tử Vi V2",
                "include_products": True,
            },
        )
        assert (brands / "tu_vi_v2" / "products" / "goi_xem.md").exists()

    def test_khong_chep_tai_lieu_goc(self, nguon):
        c, brands = nguon
        c.post(
            "/api/brands/clone",
            json={"source_id": "tu_vi_online", "id": "brand_moi", "name": "Brand Mới"},
        )
        assert not (brands / "brand_moi" / "_sources").exists(), (
            "tài liệu gốc thuộc về brand cũ"
        )

    def test_meta_duoc_dung_lai_dung_cho(self, nguon):
        c, brands = nguon
        c.post(
            "/api/brands/clone",
            json={
                "source_id": "tu_vi_online",
                "id": "phong_thuy",
                "name": "Phong Thuỷ",
                "description": "Dịch vụ phong thuỷ",
            },
        )
        meta = json.loads((brands / "phong_thuy" / "brand.json").read_text(encoding="utf-8"))

        assert meta["id"] == "phong_thuy"
        assert meta["name"] == "Phong Thuỷ"
        assert meta["description"] == "Dịch vụ phong thuỷ"
        assert meta["cloned_from"] == "tu_vi_online"
        # Ràng buộc pháp lý theo ngành thì chép sang là đúng
        assert meta["forbidden_claims"] == ["cải mệnh đổi vận"]

    def test_profile_id_doi_theo_brand_moi(self, nguon):
        c, brands = nguon
        c.post(
            "/api/brands/clone",
            json={"source_id": "tu_vi_online", "id": "phong_thuy", "name": "Phong Thuỷ"},
        )
        vp = json.loads(
            (brands / "phong_thuy" / "voice_profile.json").read_text(encoding="utf-8")
        )
        assert vp["profile_id"] == "phong_thuy", "để nguyên id cũ là trỏ nhầm brand"

    def test_nguon_khong_ton_tai(self, client):
        c, _ = client
        r = c.post("/api/brands/clone", json={"source_id": "khong_co", "id": "moi", "name": "Mới"})
        assert r.status_code == 404

    def test_ma_dich_da_ton_tai(self, nguon):
        c, _ = nguon
        brands_route.manager.create_brand("da_co", "Đã có")
        r = c.post(
            "/api/brands/clone",
            json={"source_id": "tu_vi_online", "id": "da_co", "name": "Trùng"},
        )
        assert r.status_code == 409

    def test_khong_the_nhan_ban_vao_chinh_no(self, nguon):
        c, _ = nguon
        r = c.post(
            "/api/brands/clone",
            json={"source_id": "tu_vi_online", "id": "tu_vi_online", "name": "X"},
        )
        assert r.status_code == 400

    def test_ma_sai_format_bi_chan(self, nguon):
        c, _ = nguon
        r = c.post(
            "/api/brands/clone",
            json={"source_id": "tu_vi_online", "id": "../../etc", "name": "Xấu"},
        )
        assert r.status_code == 400
        assert "knowledge_base" not in r.text
