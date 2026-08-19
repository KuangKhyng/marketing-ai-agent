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


# === R3: cache phải đổi khi knowledge / prompt / model đổi ===


class TestVersionTheoHeThong:
    """
    Trước đây key chỉ gồm raw_input + brand + brief + strategy. Sửa
    knowledge_base xong chạy lại đúng brief đó vẫn nhận content CŨ — người dùng
    tin vào thứ đã lỗi thời, mà knowledge_base lại là nguồn sự thật.
    """

    def test_sua_knowledge_thi_doi_key(self, brief):
        cu = {"product": "Không dùng cho phụ nữ mang thai", "policies": "P"}
        moi = {"product": "Dùng được cho phụ nữ mang thai", "policies": "P"}

        assert campaign_cache.content_key(RAW, "abc", brief, "S", cu) != \
               campaign_cache.content_key(RAW, "abc", brief, "S", moi)

    def test_sua_knowledge_thi_doi_ca_key_chien_luoc(self, brief):
        cu = {"brand": "Quán cà phê rang mộc"}
        moi = {"brand": "Quán cà phê rang mộc, mở thêm chi nhánh quận 3"}

        assert campaign_cache.strategy_key(RAW, "abc", brief, cu) != \
               campaign_cache.strategy_key(RAW, "abc", brief, moi)

    def test_knowledge_giong_nhau_thi_giu_nguyen_key(self, brief):
        ctx = {"product": "X", "policies": "Y"}
        assert campaign_cache.content_key(RAW, "abc", brief, "S", ctx) == \
               campaign_cache.content_key(RAW, "abc", brief, "S", dict(ctx))

    def test_metadata_khong_lam_doi_key(self, brief):
        """loaded_docs chỉ là ghi chép, không ảnh hưởng nội dung sinh ra."""
        a = {"product": "X", "loaded_docs": ["product:mot"]}
        b = {"product": "X", "loaded_docs": ["product:mot", "product:hai"]}
        assert campaign_cache.content_key(RAW, "abc", brief, "S", a) == \
               campaign_cache.content_key(RAW, "abc", brief, "S", b)

    def test_sua_prompt_thi_doi_key(self, brief, tmp_path, monkeypatch):
        import api.cache as cache_mod

        truoc = campaign_cache.content_key(RAW, "abc", brief, "S", {"product": "X"})

        gia = tmp_path / "prompt_gia.md"
        gia.write_text("prompt đã sửa", encoding="utf-8")
        monkeypatch.setattr(cache_mod, "_SYSTEM_FILES", [gia])
        cache_mod._system_digest.cache_clear()

        sau = campaign_cache.content_key(RAW, "abc", brief, "S", {"product": "X"})
        cache_mod._system_digest.cache_clear()

        assert truoc != sau, "sửa prompt mà kết quả cũ vẫn được dùng lại là sai"
