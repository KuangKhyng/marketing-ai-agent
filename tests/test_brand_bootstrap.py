"""
Bootstrap knowledge base brand từ tài liệu người dùng.

Điểm cần canh nhất không phải chất lượng extract (đó là việc của prompt), mà
là: draft KHÔNG được tự ghi đè, và apply chỉ ghi đúng thứ được duyệt.
knowledge_base là ground truth của pipeline nên ghi nhầm vào đây là làm hỏng
mọi campaign về sau.
"""
import json

import pytest

import src.knowledge.brand_manager as bm_mod
from src.knowledge import brand_bootstrap as bb
from src.knowledge.brand_manager import BrandManager


@pytest.fixture
def brands_dir(tmp_path, monkeypatch):
    d = tmp_path / "brands"
    d.mkdir()
    monkeypatch.setattr(bm_mod, "BRANDS_DIR", d)
    return d


@pytest.fixture
def manager(brands_dir):
    m = BrandManager()
    m.create_brand("ca_phe_abc", "Cà Phê ABC")
    return m


def a_voice(**kw):
    base = dict(
        tone_primary="thân mật",
        tone_secondary="mộc mạc",
        formality=0.3,
        perspective="second_person",
        avg_sentence_length=12,
        preferred_words=["rang mộc", "mẻ nhỏ"],
        avoided_words=["rẻ"],
        emoji_style="light",
        common_emojis=["☕"],
        anti_ai_rules=["Không mở bài bằng câu hỏi tu từ chung chung"],
        tone_summary="Viết như đang kể chuyện quán, câu ngắn, không hô hào.",
        dos=["Kể một cảnh cụ thể"],
        donts=["Không dùng từ sáo rỗng"],
        hook_patterns=['Mở bằng một cảnh trong ngày ("6 giờ sáng, mẻ đầu vừa ra lò")'],
        body_structure="Cảnh cụ thể → vấn đề khách gặp → cách quán làm khác",
        cta_style="Mời nhẹ, không thúc ép",
        framework_notes="Bài 150-250 từ, 3 hashtag",
    )
    base.update(kw)
    return bb.VoiceExtraction(**base)


def a_brand(**kw):
    base = dict(
        identity="Quán cà phê specialty ở quận 1, rang tại chỗ mỗi ngày.",
        mission="Để người Sài Gòn uống cà phê tươi",
        usp="Rang mỗi ngày, không bán hàng tồn quá 48 giờ",
        values=["Minh bạch nguồn hạt"],
        products=[
            bb.ProductDraft(name="Cà phê rang mộc", summary="Hạt Arabica Cầu Đất", details="250g"),
        ],
        audience=bb.AudienceDraft(
            persona_name="Dân văn phòng",
            description="Người đi làm 25-35 tuổi quanh quận 1",
            age_range="25-35",
            pain_points=["Không tìm được cà phê tươi gần chỗ làm"],
            motivations=["Uống ngon mà không mất thời gian"],
        ),
        forbidden_claims=["tốt nhất Việt Nam"],
        mandatory_terms=[],
        uncertain=["Tài liệu chưa nói về chính sách giao hàng"],
    )
    base.update(kw)
    return bb.BrandExtraction(**base)


# === Dựng markdown ===


class TestRender:
    def test_tone_of_voice_co_du_phan(self):
        md = bb.render_tone_of_voice(a_voice(), "Cà Phê ABC")
        assert "# Tone of Voice — Cà Phê ABC" in md
        assert "## Do's" in md and "## Don'ts" in md
        assert "Kể một cảnh cụ thể" in md
        assert "thân mật" in md

    def test_khung_bai_tach_khoi_giong_van(self):
        md = bb.render_content_framework(a_voice(), "Cà Phê ABC")
        assert "Cách mở bài" in md
        assert "6 giờ sáng" in md
        assert "Cảnh cụ thể" in md

    def test_field_rong_khong_de_lai_khoang_trong_kho_hieu(self):
        md = bb.render_content_framework(
            a_voice(body_structure="", cta_style="", framework_notes="", hook_patterns=[]), "X"
        )
        assert "chưa rút được từ bài mẫu" in md
        assert "None" not in md

    def test_identity_giu_nguyen_cho_thieu(self):
        md = bb.render_identity(a_brand(mission="", usp=""), "Cà Phê ABC")
        assert md.count("(chưa có trong tài liệu)") == 2
        assert "Rang mỗi ngày" not in md

    def test_products_gom_vao_MOT_file(self):
        """
        Retriever chỉ nạp tối đa 2 file trong products/. Tách mỗi sản phẩm một
        file là cách chắc chắn để mất sản phẩm thứ ba trở đi.
        """
        products = [
            bb.ProductDraft(name=f"Sản phẩm {i}", summary=f"Mô tả {i}") for i in range(5)
        ]
        md = bb.render_products(products)
        for i in range(5):
            assert f"## Sản phẩm {i}" in md

    def test_voice_profile_khop_schema_dang_dung(self):
        """Các node đang đọc đúng những key này — đổi là vỡ context_pack."""
        vp = bb.build_voice_profile(a_voice(), "ca_phe_abc")

        assert vp["profile_id"] == "ca_phe_abc"
        assert vp["tone"]["primary"] == "thân mật"
        assert vp["tone"]["formality"] == 0.3
        assert vp["writing_style"]["perspective"] == "second_person"
        assert vp["vocabulary"]["preferred"] == ["rang mộc", "mẻ nhỏ"]
        assert vp["vocabulary"]["emoji_style"] == "light"
        assert vp["anti_ai_rules"]


# === Draft không được tự ghi ===


class TestDraft:
    def test_draft_khong_ghi_file_nao(self, manager, brands_dir):
        truoc = sorted(p.name for p in (brands_dir / "ca_phe_abc").iterdir())
        bb.build_voice_draft(manager, "ca_phe_abc", "Cà Phê ABC", a_voice())
        sau = sorted(p.name for p in (brands_dir / "ca_phe_abc").iterdir())

        assert truoc == sau, "build_*_draft chỉ được trả về đề xuất, không được ghi"

    def test_draft_kem_noi_dung_hien_tai_de_doi_chieu(self, manager):
        draft = bb.build_voice_draft(manager, "ca_phe_abc", "Cà Phê ABC", a_voice())

        tone = next(f for f in draft.files if f.path == "tone_of_voice.md")
        assert tone.exists is True, "create_brand đã sinh file này rồi"
        assert "(Mô tả tone tại đây)" in tone.current, "phải trả về nội dung đang có"

        khung = next(f for f in draft.files if f.path == "content_framework.md")
        assert khung.exists is False, "file này chưa từng tồn tại"
        assert khung.current is None

    def test_draft_brand_co_du_ba_file(self, manager):
        draft = bb.build_brand_draft(manager, "ca_phe_abc", "Cà Phê ABC", a_brand())
        paths = {f.path for f in draft.files}

        assert paths == {
            "identity.md",
            "products/san_pham.md",
            "audience/khach_hang_chinh.md",
        }
        assert draft.brand_meta["forbidden_claims"] == ["tốt nhất Việt Nam"]
        assert "mandatory_terms" not in draft.brand_meta, "rỗng thì đừng đề xuất"

    def test_cho_khong_chac_chan_duoc_noi_ra(self, manager):
        draft = bb.build_brand_draft(manager, "ca_phe_abc", "Cà Phê ABC", a_brand())
        assert any("giao hàng" in n for n in draft.notes)

    def test_khong_co_san_pham_thi_khong_de_xuat_file_rong(self, manager):
        draft = bb.build_brand_draft(
            manager, "ca_phe_abc", "Cà Phê ABC", a_brand(products=[], audience=None)
        )
        assert {f.path for f in draft.files} == {"identity.md"}


# === Apply ===


class TestApply:
    def test_ghi_dung_thu_duoc_duyet(self, manager, brands_dir):
        draft = bb.build_voice_draft(manager, "ca_phe_abc", "Cà Phê ABC", a_voice())
        chi_lay_khung = [f for f in draft.files if f.path == "content_framework.md"]

        bb.apply_draft(manager, "ca_phe_abc", chi_lay_khung)

        brand_dir = brands_dir / "ca_phe_abc"
        assert "Cách mở bài" in (brand_dir / "content_framework.md").read_text(encoding="utf-8")
        assert "(Mô tả tone tại đây)" in (brand_dir / "tone_of_voice.md").read_text(
            encoding="utf-8"
        ), "file người dùng KHÔNG chọn thì không được đụng vào"

    def test_ghi_voice_profile_va_brand_meta(self, manager, brands_dir):
        draft = bb.build_brand_draft(manager, "ca_phe_abc", "Cà Phê ABC", a_brand())
        bb.apply_draft(
            manager,
            "ca_phe_abc",
            [],
            voice_profile=bb.build_voice_profile(a_voice(), "ca_phe_abc"),
            brand_meta=draft.brand_meta,
        )

        brand_dir = brands_dir / "ca_phe_abc"
        vp = json.loads((brand_dir / "voice_profile.json").read_text(encoding="utf-8"))
        assert vp["tone"]["primary"] == "thân mật"

        meta = json.loads((brand_dir / "brand.json").read_text(encoding="utf-8"))
        assert meta["forbidden_claims"] == ["tốt nhất Việt Nam"]
        assert meta["name"] == "Cà Phê ABC", "update_brand_meta không được xoá field khác"

    def test_khong_duyet_gi_thi_khong_ghi_gi(self, manager, brands_dir):
        truoc = (brands_dir / "ca_phe_abc" / "identity.md").read_text(encoding="utf-8")
        bb.apply_draft(manager, "ca_phe_abc", [])
        assert (brands_dir / "ca_phe_abc" / "identity.md").read_text(encoding="utf-8") == truoc

    def test_path_traversal_bi_chan(self, manager):
        """Path trong draft đến từ client nên vẫn phải qua safe_join."""
        from src.utils.paths import InvalidPathError

        doc_te = bb.FileDraft(path="../../../etc/passwd", content="xấu")
        with pytest.raises(InvalidPathError):
            bb.apply_draft(manager, "ca_phe_abc", [doc_te])


# === Giới hạn input ===


class TestInputSize:
    def test_tai_lieu_vua_phai_thi_qua(self):
        assert bb.check_input_size(["x" * 1000, "y" * 500]) == 1500

    def test_tai_lieu_qua_dai_bi_chan(self):
        with pytest.raises(ValueError, match="quá dài"):
            bb.check_input_size(["x" * (bb.MAX_INPUT_CHARS + 1)])


# === Điểm hoàn thiện phải nói thật ===


class TestCompleteness:
    def test_brand_toan_placeholder_khong_duoc_tinh_la_xong(self, manager, brands_dir):
        """
        create_brand sinh file mẫu đầy "(Thêm brand identity tại đây)" — riêng
        phần khung đó đã dài hơn 50 ký tự, nên phép đo cũ (len(file) > 50) chấm
        brand rỗng hoàn toàn là đã hoàn thành 50%.
        """
        brand = manager.get_brand("ca_phe_abc")
        assert brand["completeness"]["score"] == 0
        assert brand["completeness"]["checks"]["identity"] is False
        assert brand["completeness"]["checks"]["tone"] is False

    def test_sau_khi_bootstrap_thi_diem_len(self, manager, brands_dir):
        voice_draft = bb.build_voice_draft(manager, "ca_phe_abc", "Cà Phê ABC", a_voice())
        brand_draft = bb.build_brand_draft(manager, "ca_phe_abc", "Cà Phê ABC", a_brand())
        bb.apply_draft(manager, "ca_phe_abc", voice_draft.files + brand_draft.files)

        checks = manager.get_brand("ca_phe_abc")["completeness"]
        assert checks["score"] == 100, checks["checks"]
