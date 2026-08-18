"""
G1 + G2 — cache key phải chứa mọi thứ ảnh hưởng output.

Hai lỗi được chốt ở đây:
  A1: content cache bỏ qua chiến lược user vừa sửa
  A2: chiến lược sinh từ brief đã chỉnh ghi đè lên key của brief gốc
"""
from api.cache import campaign_cache, is_cacheable


RAW = "Tạo campaign awareness cho cà phê rang mộc"


def test_content_key_doi_khi_strategy_doi(brief):
    """A1: strategy nằm trong key => sửa strategy là cache miss."""
    k_cu = campaign_cache.content_key(RAW, "abc", brief, "Chiến lược bản 1")
    k_moi = campaign_cache.content_key(RAW, "abc", brief, "Chiến lược bản 2 sau khi user sửa")

    assert k_cu != k_moi, (
        "Cùng key nghĩa là content sẽ lấy từ cache và chiến lược đã sửa bị bỏ qua"
    )


def test_strategy_key_doi_khi_brief_doi(brief):
    """A2: brief nằm trong key => brief đã chỉnh không ghi đè key của brief gốc."""
    k_goc = campaign_cache.strategy_key(RAW, "abc", brief)

    brief_da_sua = brief.model_copy(deep=True)
    brief_da_sua.offer.product_or_service = "Cà phê phin truyền thống"
    k_sua = campaign_cache.strategy_key(RAW, "abc", brief_da_sua)

    assert k_goc != k_sua


def test_key_phan_biet_brand(brief):
    assert campaign_cache.strategy_key(RAW, "abc", brief) != campaign_cache.strategy_key(
        RAW, "xyz", brief
    )


def test_key_on_dinh_voi_cung_input(brief):
    """Cùng input phải ra cùng key, nếu không cache vô dụng."""
    assert campaign_cache.strategy_key(RAW, "abc", brief) == campaign_cache.strategy_key(
        RAW, "abc", brief
    )


def test_key_khong_nhap_nhem_ranh_gioi(brief):
    """('a','bc') không được ra cùng key với ('ab','c')."""
    assert campaign_cache.strategy_key("a", "bc", None) != campaign_cache.strategy_key(
        "ab", "c", None
    )


def test_strategy_va_content_khac_namespace(brief):
    assert campaign_cache.strategy_key(RAW, "abc", brief) != campaign_cache.content_key(
        RAW, "abc", brief, None
    )


class TestIsCacheable:
    def test_run_moi_thi_dung_duoc_cache(self):
        assert is_cacheable({"raw_input": RAW}) is True

    def test_co_feedback_chien_luoc_thi_khong_cache(self):
        """feedback = user muốn bản KHÁC, trả bản cũ là sai."""
        assert is_cacheable({"strategy_feedback": "Tone casual hơn"}) is False

    def test_da_qua_vong_review_thi_khong_cache(self):
        assert is_cacheable({"review_result": object()}) is False
