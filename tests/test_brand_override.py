"""
F1 — bất biến chống LLM bịa thông tin brand.

`_override_brand_from_state` là chốt chặn kiến trúc: brief_parser KHÔNG BAO GIỜ
được để LLM quyết định brand. Brand đến từ lựa chọn trên UI, và mọi thứ LLM tự
nghĩ ra về brand đều phải bị ghi đè.

Vì sao đáng canh kỹ: `forbidden_claims` và `mandatory_terms` được reviewer dùng
làm QUY TẮC CỨNG (src/nodes/reviewer.py::_run_rule_checks) — chiều nào vi phạm
là trượt bất kể điểm LLM. Nếu một cụm từ do LLM bịa lọt vào đây, hệ thống sẽ
bắt mọi bài phải chứa một từ chẳng ai yêu cầu, hoặc cấm một điều chẳng ai cấm.
"""
import pytest

import src.knowledge.brand_manager as bm_mod
import src.nodes.brief_parser as bp
from src.models.brief import (
    AudienceSpec,
    BrandSpec,
    CampaignBrief,
    CampaignGoal,
    Channel,
    Deliverable,
    OfferSpec,
)
from src.knowledge.brand_manager import BrandManager


@pytest.fixture
def brands_dir(tmp_path, monkeypatch):
    d = tmp_path / "brands"
    d.mkdir()
    monkeypatch.setattr(bm_mod, "BRANDS_DIR", d)
    return d


def brief_llm_bia_dat():
    """Brief như thể LLM vừa trả về, với brand hoàn toàn bịa."""
    return CampaignBrief(
        goal=CampaignGoal.AWARENESS,
        brand=BrandSpec(
            name="Thương Hiệu LLM Tự Nghĩ Ra",
            voice_profile_id="ho_cau",
            forbidden_claims=["điều LLM tưởng là cấm"],
            mandatory_terms=["từ LLM tưởng là bắt buộc"],
        ),
        audience=AudienceSpec(persona_description="ai đó"),
        offer=OfferSpec(product_or_service="gì đó", key_message="x", cta="y"),
        channels=[Channel.FACEBOOK],
        deliverables=[Deliverable.POST],
    )


class TestGenericMode:
    """Không chọn brand nào thì mọi thứ LLM bịa phải bị xoá sạch."""

    def test_xoa_het_moi_thu_llm_bia(self, brands_dir):
        out = bp._override_brand_from_state(brief_llm_bia_dat(), {"brand_id": None})

        assert out.brand.name == ""
        assert out.brand.voice_profile_id == "default"
        assert out.brand.forbidden_claims == []
        assert out.brand.mandatory_terms == []

    def test_thieu_han_khoa_brand_id(self, brands_dir):
        out = bp._override_brand_from_state(brief_llm_bia_dat(), {})
        assert out.brand.name == ""
        assert out.brand.forbidden_claims == []

    def test_brand_id_rong_cung_tinh_la_generic(self, brands_dir):
        out = bp._override_brand_from_state(brief_llm_bia_dat(), {"brand_id": ""})
        assert out.brand.name == ""
        assert out.brand.mandatory_terms == []


class TestBrandCoThat:
    """Chọn brand có thật thì lấy từ brand.json, không lấy từ LLM."""

    def test_lay_du_lieu_tu_kho_brand(self, brands_dir):
        m = BrandManager()
        m.create_brand("ca_phe_abc", "Cà Phê ABC")
        m.update_brand_meta(
            "ca_phe_abc",
            {"forbidden_claims": ["ngon nhất Việt Nam"], "mandatory_terms": ["Cà Phê ABC"]},
        )

        out = bp._override_brand_from_state(brief_llm_bia_dat(), {"brand_id": "ca_phe_abc"})

        assert out.brand.name == "Cà Phê ABC"
        assert out.brand.voice_profile_id == "ca_phe_abc"
        assert out.brand.forbidden_claims == ["ngon nhất Việt Nam"]
        assert out.brand.mandatory_terms == ["Cà Phê ABC"]

    def test_brand_khong_khai_rang_buoc_thi_ra_rong(self, brands_dir):
        """Không khai báo nghĩa là không có, KHÔNG phải là giữ cái LLM bịa."""
        BrandManager().create_brand("ca_phe_abc", "Cà Phê ABC")

        out = bp._override_brand_from_state(brief_llm_bia_dat(), {"brand_id": "ca_phe_abc"})

        assert out.brand.forbidden_claims == []
        assert out.brand.mandatory_terms == []


class TestKhongXacNhanDuoc:
    """
    Không tra được thông tin brand thì ràng buộc do LLM bịa TUYỆT ĐỐI không
    được sống sót — reviewer sẽ coi chúng là quy tắc cứng.
    """

    def test_brand_id_khong_ton_tai(self, brands_dir):
        out = bp._override_brand_from_state(brief_llm_bia_dat(), {"brand_id": "khong_co_that"})

        assert out.brand.name == ""
        assert out.brand.voice_profile_id == "default"
        assert out.brand.forbidden_claims == [], (
            "ràng buộc LLM bịa lọt vào reviewer sẽ cấm những điều chẳng ai cấm"
        )
        assert out.brand.mandatory_terms == [], (
            "mandatory_terms bịa sẽ làm MỌI bài trượt vì thiếu một từ chẳng ai yêu cầu"
        )

    def test_kho_brand_loi(self, brands_dir, monkeypatch):
        def no_len(self, brand_id):
            raise OSError("volume không đọc được")

        monkeypatch.setattr(BrandManager, "get_brand", no_len)

        out = bp._override_brand_from_state(brief_llm_bia_dat(), {"brand_id": "ca_phe_abc"})

        assert out.brand.forbidden_claims == []
        assert out.brand.mandatory_terms == []


class TestKhongDungToiPhanKhac:
    """Chỉ được sửa phần brand, không đụng vào phần còn lại của brief."""

    def test_giu_nguyen_goal_offer_audience(self, brands_dir):
        goc = brief_llm_bia_dat()
        out = bp._override_brand_from_state(goc, {"brand_id": None})

        assert out.goal is CampaignGoal.AWARENESS
        assert out.offer.product_or_service == "gì đó"
        assert out.audience.persona_description == "ai đó"
        assert out.channels == [Channel.FACEBOOK]
