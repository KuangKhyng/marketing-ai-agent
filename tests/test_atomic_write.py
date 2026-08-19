"""
Roadmap mục 9 — ghi file không được để lại trạng thái nửa vời.

`path.write_text()` cắt file về rỗng rồi ghi dần. Crash, hết dung lượng, hoặc
container bị kill ở giữa để lại một file cụt — mà đây là knowledge base,
session state và file bàn giao, tức nguồn sự thật của cả pipeline.
"""
import pickle

import pytest

import src.knowledge.brand_manager as bm_mod
from src.knowledge import brand_bootstrap as bb
from src.knowledge.brand_manager import BrandManager
from src.utils.paths import atomic_write_bytes, atomic_write_many, atomic_write_text


class TestGhiMotFile:
    def test_ghi_va_doc_lai_duoc(self, tmp_path):
        f = tmp_path / "sub" / "a.md"
        atomic_write_text(f, "nội dung tiếng Việt")
        assert f.read_text(encoding="utf-8") == "nội dung tiếng Việt"

    def test_khong_de_lai_file_tam(self, tmp_path):
        atomic_write_text(tmp_path / "a.md", "x")
        assert [f.name for f in tmp_path.iterdir()] == ["a.md"]

    def test_ghi_de_giu_nguyen_ban_cu_khi_hong(self, tmp_path, monkeypatch):
        """
        Điểm chính: ghi hỏng thì bản CŨ phải còn nguyên, không bị cắt cụt.
        """
        f = tmp_path / "a.md"
        atomic_write_text(f, "bản cũ đầy đủ")

        goc = bm_mod  # giữ tham chiếu để monkeypatch không rò
        import src.utils.paths as paths_mod

        def hong(*a, **kw):
            raise OSError("hết dung lượng")

        monkeypatch.setattr(paths_mod.os, "replace", hong)

        with pytest.raises(OSError):
            atomic_write_text(f, "bản mới")

        assert f.read_text(encoding="utf-8") == "bản cũ đầy đủ"
        assert [x.name for x in tmp_path.iterdir()] == ["a.md"], "file tạm phải được dọn"

    def test_ghi_nhi_phan(self, tmp_path):
        f = tmp_path / "state.pkl"
        atomic_write_bytes(f, pickle.dumps({"a": 1}))
        assert pickle.loads(f.read_bytes()) == {"a": 1}


class TestGhiNhieuFile:
    def test_ghi_het(self, tmp_path):
        atomic_write_many([
            (tmp_path / "a.md", b"A"),
            (tmp_path / "sub" / "b.md", b"B"),
        ])
        assert (tmp_path / "a.md").read_bytes() == b"A"
        assert (tmp_path / "sub" / "b.md").read_bytes() == b"B"

    def test_hong_o_giai_doan_ghi_thi_khong_dung_file_that_nao(self, tmp_path, monkeypatch):
        """
        Giai đoạn 1 hỏng (hết dung lượng ở file thứ hai) thì file thứ nhất cũng
        chưa được cam kết — brand không bị nửa mới nửa cũ.
        """
        (tmp_path / "a.md").write_text("bản cũ A", encoding="utf-8")

        import src.utils.paths as paths_mod

        that = paths_mod.tempfile.mkstemp
        dem = {"n": 0}

        def mkstemp_hong(*a, **kw):
            dem["n"] += 1
            if dem["n"] == 2:
                raise OSError("hết dung lượng")
            return that(*a, **kw)

        monkeypatch.setattr(paths_mod.tempfile, "mkstemp", mkstemp_hong)

        with pytest.raises(OSError):
            atomic_write_many([(tmp_path / "a.md", b"moi A"), (tmp_path / "b.md", b"moi B")])

        assert (tmp_path / "a.md").read_text(encoding="utf-8") == "bản cũ A"
        assert not (tmp_path / "b.md").exists()
        assert [f.name for f in tmp_path.iterdir()] == ["a.md"], "không được để lại file tạm"

    def test_danh_sach_rong(self, tmp_path):
        assert atomic_write_many([]) == []


class TestApplyDraft:
    """apply_draft ghi nhiều file cùng lúc — phải có một điểm cam kết chung."""

    @pytest.fixture
    def manager(self, tmp_path, monkeypatch):
        d = tmp_path / "brands"
        d.mkdir()
        monkeypatch.setattr(bm_mod, "BRANDS_DIR", d)
        m = BrandManager()
        m.create_brand("ca_phe_abc", "Cà Phê ABC")
        return m, d

    def test_ghi_het_cac_file_duoc_duyet(self, manager):
        m, brands = manager
        bb.apply_draft(m, "ca_phe_abc", [
            bb.FileDraft(path="identity.md", content="Nhận diện mới"),
            bb.FileDraft(path="products/san_pham.md", content="Sản phẩm mới"),
        ])

        d = brands / "ca_phe_abc"
        assert "Nhận diện mới" in (d / "identity.md").read_text(encoding="utf-8")
        assert "Sản phẩm mới" in (d / "products" / "san_pham.md").read_text(encoding="utf-8")

    def test_hong_giua_chung_thi_khong_de_lai_brand_nua_moi_nua_cu(self, manager, monkeypatch):
        m, brands = manager
        d = brands / "ca_phe_abc"
        goc_identity = (d / "identity.md").read_text(encoding="utf-8")

        import src.utils.paths as paths_mod

        that = paths_mod.tempfile.mkstemp
        dem = {"n": 0}

        def mkstemp_hong(*a, **kw):
            dem["n"] += 1
            if dem["n"] == 2:
                raise OSError("volume đầy")
            return that(*a, **kw)

        monkeypatch.setattr(paths_mod.tempfile, "mkstemp", mkstemp_hong)

        with pytest.raises(OSError):
            bb.apply_draft(m, "ca_phe_abc", [
                bb.FileDraft(path="identity.md", content="Nhận diện MỚI"),
                bb.FileDraft(path="products/san_pham.md", content="Sản phẩm MỚI"),
            ])

        assert (d / "identity.md").read_text(encoding="utf-8") == goc_identity, (
            "identity đổi mà sản phẩm chưa là brand tự mâu thuẫn — mà cả hai đều "
            "là nguồn sự thật reviewer dùng để chấm"
        )
        assert not (d / "products" / "san_pham.md").exists()

    def test_cap_nhat_updated_at(self, manager):
        import json

        m, brands = manager
        truoc = json.loads((brands / "ca_phe_abc" / "brand.json").read_text(encoding="utf-8"))

        bb.apply_draft(m, "ca_phe_abc", [bb.FileDraft(path="identity.md", content="x" * 100)])

        sau = json.loads((brands / "ca_phe_abc" / "brand.json").read_text(encoding="utf-8"))
        assert sau["updated_at"] >= truoc["updated_at"]
