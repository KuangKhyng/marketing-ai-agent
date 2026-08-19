"""
F2 — retriever: module quyết định MỌI campaign nhìn thấy gì.

Đây là logic thuần (đọc file + chấm điểm từ khoá), không cần API, mà trước đó
chỉ có 15% được chạy qua. Sai ở đây thì content sai giọng, sai sản phẩm, hoặc
mất hẳn ràng buộc pháp lý — và không có gì báo cho ai biết.
"""
import json

import pytest

import src.knowledge.retriever as rt
from src.models.brief import (
    AudienceSpec,
    BrandSpec,
    CampaignBrief,
    CampaignGoal,
    Channel,
    Deliverable,
    OfferSpec,
)


@pytest.fixture
def kb(tmp_path, monkeypatch):
    """Dựng một knowledge_base thật trên đĩa tạm."""
    knowledge = tmp_path / "knowledge_base"
    brands = knowledge / "brands"
    glob = knowledge / "_global"
    (glob / "platforms").mkdir(parents=True)
    (glob / "policies").mkdir(parents=True)
    brands.mkdir(parents=True)

    (glob / "platforms" / "facebook.md").write_text("Luật Facebook", encoding="utf-8")
    (glob / "platforms" / "tiktok.md").write_text("Luật TikTok", encoding="utf-8")
    (glob / "policies" / "chung.md").write_text("Quy định chung", encoding="utf-8")

    monkeypatch.setattr(rt, "KNOWLEDGE_DIR", knowledge)
    monkeypatch.setattr(rt, "BRANDS_DIR", brands)
    monkeypatch.setattr(rt, "GLOBAL_DIR", glob)
    # lru_cache giữ nội dung theo (path, mtime); test tạo file mới liên tục
    rt._read_file_cached.cache_clear()
    return brands


def a_brand(brands, brand_id="ca_phe_abc", **files):
    d = brands / brand_id
    d.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        path = d / name.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return d


def a_brief(product="cà phê rang mộc", audience="dân văn phòng", channels=None):
    return CampaignBrief(
        goal=CampaignGoal.AWARENESS,
        brand=BrandSpec(name="X"),
        audience=AudienceSpec(persona_description=audience),
        offer=OfferSpec(product_or_service=product, key_message="tươi mỗi ngày", cta="ghé quán"),
        channels=channels or [Channel.FACEBOOK],
        deliverables=[Deliverable.POST],
    )


# === Luôn nạp: luật nền tảng + quy định chung ===


class TestLuonNap:
    def test_chi_nap_platform_cua_kenh_duoc_chon(self, kb):
        ctx = rt.build_context_pack(a_brief(channels=[Channel.FACEBOOK]))

        assert ctx["platform_rules"]["facebook"] == "Luật Facebook"
        assert "tiktok" not in ctx["platform_rules"], (
            "nạp luật kênh không dùng chỉ tổ nhồi context và tốn tiền"
        )

    def test_quy_dinh_chung_luon_co(self, kb):
        ctx = rt.build_context_pack(a_brief())
        assert "Quy định chung" in ctx["policies"]

    def test_ghi_lai_da_nap_nhung_gi(self, kb):
        ctx = rt.build_context_pack(a_brief())
        assert "platform:facebook" in ctx["loaded_docs"]
        assert "global_policy:chung" in ctx["loaded_docs"]


# === Chế độ generic ===


class TestGeneric:
    def test_khong_chon_brand_thi_dung_giong_mac_dinh(self, kb):
        ctx = rt.build_context_pack(a_brief())

        assert ctx["mode"] == "generic"
        assert ctx["voice_profile"]["profile_id"] == "generic"
        assert ctx["brand"] == ""

    def test_brand_khong_ton_tai_thi_roi_ve_generic_chu_khong_vo(self, kb):
        ctx = rt.build_context_pack(a_brief(), brand_id="khong_co_that")

        assert ctx["mode"] == "generic"
        assert ctx["voice_profile"]["profile_id"] == "generic"
        assert "Quy định chung" in ctx["policies"], "quy định chung vẫn phải còn"

    def test_brand_id_doc_hai_khong_thoat_ra_ngoai(self, kb):
        """brand_id đi thẳng từ input người dùng."""
        ctx = rt.build_context_pack(a_brief(), brand_id="../../../etc")
        assert ctx["mode"] == "generic"


# === Chế độ có brand ===


class TestCoBrand:
    def test_gom_du_bon_file_nhan_dien(self, kb):
        a_brand(
            kb,
            **{
                "identity.md": "Nhận diện brand",
                "tone_of_voice.md": "Giọng brand",
                "content_framework.md": "Khung bài brand",
                "visual_guidelines.md": "Hình ảnh brand",
            },
        )
        ctx = rt.build_context_pack(a_brief(), brand_id="ca_phe_abc")

        assert ctx["mode"] == "branded"
        for phan in ("Nhận diện brand", "Giọng brand", "Khung bài brand", "Hình ảnh brand"):
            assert phan in ctx["brand"], f"thiếu {phan}"

    def test_content_framework_duoc_nap(self, kb):
        """File này sinh ra từ bước nạp liệu — không nạp thì công cốc."""
        a_brand(kb, **{"content_framework.md": "Mở bài bằng một cảnh cụ thể"})
        ctx = rt.build_context_pack(a_brief(), brand_id="ca_phe_abc")

        assert "Mở bài bằng một cảnh cụ thể" in ctx["brand"]
        assert "brand:content_framework" in ctx["loaded_docs"]

    def test_quy_dinh_rieng_cua_brand_cong_them_chu_khong_thay_the(self, kb):
        a_brand(kb, **{"policies__rieng.md": "Không nói cam kết chữa khỏi"})
        ctx = rt.build_context_pack(a_brief(), brand_id="ca_phe_abc")

        assert "Không nói cam kết chữa khỏi" in ctx["policies"]
        assert "Quy định chung" in ctx["policies"], "quy định chung không được biến mất"

    def test_voice_profile_cua_brand_thang_ban_mac_dinh(self, kb):
        d = a_brand(kb)
        (d / "voice_profile.json").write_text(
            json.dumps({"profile_id": "ca_phe_abc", "tone": {"primary": "mộc mạc"}}),
            encoding="utf-8",
        )
        ctx = rt.build_context_pack(a_brief(), brand_id="ca_phe_abc")

        assert ctx["voice_profile"]["tone"]["primary"] == "mộc mạc"

    def test_brand_khong_co_voice_profile_thi_dung_mac_dinh(self, kb):
        a_brand(kb, **{"identity.md": "x"})
        ctx = rt.build_context_pack(a_brief(), brand_id="ca_phe_abc")
        assert ctx["voice_profile"]["profile_id"] == "generic"

    def test_lay_ten_brand_tu_brand_json(self, kb):
        d = a_brand(kb)
        (d / "brand.json").write_text(
            json.dumps({"id": "ca_phe_abc", "name": "Cà Phê ABC"}, ensure_ascii=False),
            encoding="utf-8",
        )
        ctx = rt.build_context_pack(a_brief(), brand_id="ca_phe_abc")
        assert ctx["brand_name"] == "Cà Phê ABC"


# === Chọn file theo từ khoá ===


class TestChonFile:
    def test_mot_file_khop_thi_nap(self, kb):
        a_brand(kb, **{"products__ca_phe.md": "Cà phê rang mộc, hạt Arabica"})
        ctx = rt.build_context_pack(a_brief(product="cà phê rang mộc"), brand_id="ca_phe_abc")

        assert "Arabica" in ctx["product"]
        assert ctx["product_evidence"] is True

    def test_chon_dung_file_khop_ten(self, kb):
        a_brand(
            kb,
            **{
                "products__ca_phe_rang_moc.md": "Hạt Arabica Cầu Đất",
                "products__banh_ngot.md": "Bánh su kem",
                "products__tra_sua.md": "Trà sữa trân châu",
            },
        )
        ctx = rt.build_context_pack(
            a_brief(product="cà phê rang mộc"), brand_id="ca_phe_abc"
        )

        assert "Hạt Arabica Cầu Đất" in ctx["product"]
        assert "Trà sữa trân châu" not in ctx["product"]

    def test_nap_toi_da_hai_file_san_pham(self, kb):
        """
        Ràng buộc thật của hệ thống: quá hai file là bị cắt bỏ âm thầm. Đây là
        lý do bước nạp liệu gom mọi sản phẩm vào MỘT file.
        """
        a_brand(
            kb,
            **{f"products__ca_phe_{i}.md": f"Cà phê loại {i}" for i in range(5)},
        )
        ctx = rt.build_context_pack(a_brief(product="cà phê"), brand_id="ca_phe_abc")

        so_file_nap = sum(1 for i in range(5) if f"Cà phê loại {i}" in ctx["product"])
        assert so_file_nap == 2

    def test_khong_khop_thi_noi_khong_biet_chu_khong_lay_bua(self, kb):
        """
        Đây là hành vi ĐÃ ĐỔI. Trước đây không khớp thì lấy files[0]:

            User: kem chống nắng trẻ em -> không khớp -> nạp "Serum trị mụn"
            -> LLM coi Serum là sự thật về sản phẩm đang viết

        Trong hệ AI, không biết tốt hơn biết sai — nhất là khi reviewer chấm
        factuality dựa trên chính tài liệu bị nạp nhầm nên không bắt được.
        """
        a_brand(
            kb,
            **{
                "products__serum_tri_mun.md": "Serum trị mụn, chứa BHA",
                "products__toner.md": "Toner cân bằng da",
            },
        )
        ctx = rt.build_context_pack(
            a_brief(product="kem chống nắng trẻ em"), brand_id="ca_phe_abc"
        )

        assert "Serum" not in ctx["product"], "không được lấy bừa tài liệu không liên quan"
        assert "BHA" not in ctx["product"]
        assert ctx["product_evidence"] is False
        assert "không bịa" in ctx["product"].lower(), "phải dặn LLM đừng bịa"

    def test_khong_co_tai_lieu_thi_dan_llm_dung_bia(self, kb):
        a_brand(kb, **{"identity.md": "x"})
        ctx = rt.build_context_pack(a_brief(), brand_id="ca_phe_abc")

        assert ctx["product_evidence"] is False
        assert "KHÔNG tìm được tài liệu sản phẩm" in ctx["product"]

    def test_che_do_generic_cung_khai_bao_khong_co_bang_chung(self, kb):
        ctx = rt.build_context_pack(a_brief())
        assert ctx["product_evidence"] is False
        assert "KHÔNG tìm được tài liệu sản phẩm" in ctx["product"]

    def test_quet_toan_van_chu_khong_chi_500_ky_tu_dau(self, kb):
        """Từ khoá nằm cuối file dài vẫn phải tính là khớp."""
        dai = "Phần mở đầu dài dòng. " * 60 + "\n\nSản phẩm: cà phê rang mộc Cầu Đất"
        a_brand(kb, **{"products__mot.md": dai, "products__hai.md": "Trà sữa"})

        ctx = rt.build_context_pack(a_brief(product="cà phê rang mộc"), brand_id="ca_phe_abc")
        assert "Cầu Đất" in ctx["product"]

    def test_bo_qua_file_bat_dau_bang_gach_duoi(self, kb):
        a_brand(kb, **{"products___template.md": "(Thêm sản phẩm tại đây)"})
        ctx = rt.build_context_pack(a_brief(), brand_id="ca_phe_abc")
        assert "(Thêm" not in ctx["product"], "mẫu rỗng không được vào context"




# === Tách từ khoá ===


class TestTuKhoa:
    def test_bo_tu_vo_nghia(self, kb):
        kws = rt._extract_keywords("Tạo campaign cho dịch vụ xem tử vi online")
        for bo in ("tạo", "campaign", "cho", "dịch", "vụ", "online"):
            assert bo not in kws, f"'{bo}' là stop word, không được tính là từ khoá"
        assert "tử" in kws or "vi" in kws

    def test_giu_dau_tieng_viet(self, kb):
        assert "phê" in rt._extract_keywords("cà phê rang mộc")

    def test_khong_lap_tu(self, kb):
        kws = rt._extract_keywords("cà phê cà phê cà phê")
        assert len(kws) == len(set(kws))

    def test_chuoi_rong(self, kb):
        assert rt._extract_keywords("") == []
