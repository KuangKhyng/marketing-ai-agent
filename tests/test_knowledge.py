"""
Knowledge base: chặn ghi đè brand, và seed vào volume trắng.

Cả hai đều là chỗ mất dữ liệu im lặng nếu sai.
"""
import pytest

import src.knowledge.brand_manager as bm_mod
import src.knowledge.seed as seed_mod
from src.knowledge.brand_manager import BrandExistsError, BrandManager


@pytest.fixture
def brands_dir(tmp_path, monkeypatch):
    d = tmp_path / "brands"
    d.mkdir()
    monkeypatch.setattr(bm_mod, "BRANDS_DIR", d)
    return d


class TestCreateBrand:
    def test_tao_brand_moi_binh_thuong(self, brands_dir):
        meta = BrandManager().create_brand("caphe_abc", "Cà Phê ABC")

        assert meta["name"] == "Cà Phê ABC"
        assert (brands_dir / "caphe_abc" / "identity.md").exists()
        assert (brands_dir / "caphe_abc" / "voice_profile.json").exists()

    def test_khong_ghi_de_brand_da_co_du_thieu_brand_json(self, brands_dir):
        """
        get_brand() trả None khi thiếu brand.json, nên route sẽ cho qua.
        create_brand phải tự chặn, nếu không identity.md của user bị ghi đè.
        """
        existing = brands_dir / "caphe_abc"
        existing.mkdir()
        (existing / "identity.md").write_text("nội dung user đã viết", encoding="utf-8")
        # cố tình KHÔNG có brand.json

        manager = BrandManager()
        assert manager.get_brand("caphe_abc") is None  # route sẽ tưởng là chưa có

        with pytest.raises(BrandExistsError):
            manager.create_brand("caphe_abc", "Cà Phê ABC")

        assert (existing / "identity.md").read_text(encoding="utf-8") == "nội dung user đã viết"

    def test_thu_muc_rong_thi_tao_duoc(self, brands_dir):
        (brands_dir / "caphe_abc").mkdir()
        meta = BrandManager().create_brand("caphe_abc", "Cà Phê ABC")
        assert meta["id"] == "caphe_abc"


class TestSeed:
    @pytest.fixture
    def dirs(self, tmp_path, monkeypatch):
        kb = tmp_path / "knowledge_base"
        seed = tmp_path / "seed_knowledge"
        (seed / "brands" / "tuvionline").mkdir(parents=True)
        (seed / "brands" / "tuvionline" / "identity.md").write_text("seed", encoding="utf-8")
        (seed / "_global" / "platforms").mkdir(parents=True)
        (seed / "_global" / "platforms" / "facebook.md").write_text("fb", encoding="utf-8")

        monkeypatch.setattr(seed_mod, "KNOWLEDGE_DIR", kb)
        monkeypatch.setattr(seed_mod, "SEED_DIR", seed)
        return kb, seed

    def test_volume_trang_thi_nap_day_du(self, dirs):
        kb, _ = dirs
        assert seed_mod.seed_knowledge_base() == 2
        assert (kb / "brands" / "tuvionline" / "identity.md").read_text(encoding="utf-8") == "seed"
        assert (kb / "_global" / "platforms" / "facebook.md").exists()

    def test_khong_ghi_de_file_user_da_sua(self, dirs):
        kb, _ = dirs
        target = kb / "brands" / "tuvionline" / "identity.md"
        target.parent.mkdir(parents=True)
        target.write_text("user đã sửa trên volume", encoding="utf-8")

        copied = seed_mod.seed_knowledge_base()

        assert copied == 1  # chỉ file facebook.md còn thiếu
        assert target.read_text(encoding="utf-8") == "user đã sửa trên volume"

    def test_chay_lai_khong_lam_gi_them(self, dirs):
        seed_mod.seed_knowledge_base()
        assert seed_mod.seed_knowledge_base() == 0

    def test_khong_co_seed_dir_thi_bo_qua(self, tmp_path, monkeypatch):
        """Chạy local: knowledge_base là thư mục thật, không có seed_knowledge."""
        monkeypatch.setattr(seed_mod, "KNOWLEDGE_DIR", tmp_path / "kb")
        monkeypatch.setattr(seed_mod, "SEED_DIR", tmp_path / "khong_ton_tai")
        assert seed_mod.seed_knowledge_base() == 0
