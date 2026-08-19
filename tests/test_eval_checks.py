"""
Logic chấm điểm của eval cũng là code, nên cũng phải được test.

Nếu phép kiểm sai thì cả bộ eval nói dối — tệ hơn không có eval, vì lúc đó
người ta tin vào một con số sai.

Test ở đây chạy offline như mọi test khác. Bản thân việc CHẠY eval (gọi API)
thì nằm ngoài pytest — xem evals/README.md.
"""
import pytest

from evals import checks


class TestKiemContext:
    def test_du_tai_lieu_bat_buoc(self):
        ctx = {"loaded_docs": ["brand:identity", "product:ca_phe"]}
        r = checks.kiem_da_nap(ctx, ["brand:identity"])
        assert r.passed

    def test_thieu_tai_lieu_bat_buoc(self):
        ctx = {"loaded_docs": ["brand:identity"]}
        r = checks.kiem_da_nap(ctx, ["brand:identity", "product:ca_phe"])

        assert not r.passed
        assert "product:ca_phe" in r.detail

    def test_bat_duoc_tai_lieu_nap_nham(self):
        """Phép kiểm quan trọng nhất của tầng retrieval."""
        ctx = {"loaded_docs": ["product:serum_tri_mun"]}
        r = checks.kiem_khong_nap(ctx, ["product:serum_tri_mun"])

        assert not r.passed
        assert "serum" in r.detail

    def test_bang_chung_dung_ky_vong(self):
        assert checks.kiem_bang_chung({"product_evidence": False}, False).passed
        assert not checks.kiem_bang_chung({"product_evidence": True}, False).passed

    def test_thieu_khoa_thi_coi_nhu_khong_co_bang_chung(self):
        assert checks.kiem_bang_chung({}, False).passed


class TestKiemNoiDung:
    def test_bat_duoc_cum_bi_cam(self):
        r = checks.kiem_khong_chua("Dịch vụ giúp bạn CẢI MỆNH ĐỔI VẬN", ["cải mệnh đổi vận"])
        assert not r.passed

    def test_khong_phan_biet_hoa_thuong(self):
        assert not checks.kiem_khong_chua("Đảm Bảo 100%", ["đảm bảo 100%"]).passed

    def test_khong_phan_biet_khoang_trang_thua(self):
        """Xuống dòng giữa câu không được làm lọt cụm bị cấm."""
        assert not checks.kiem_khong_chua("cải mệnh\n   đổi vận", ["cải mệnh đổi vận"]).passed

    def test_sach_thi_dat(self):
        assert checks.kiem_khong_chua("Xem tử vi để hiểu mình hơn", ["cải mệnh"]).passed

    def test_co_it_nhat_mot_cum(self):
        assert checks.kiem_co_it_nhat_mot("Luận giải lá số", ["tử vi", "lá số"]).passed
        assert not checks.kiem_co_it_nhat_mot("Bán cà phê", ["tử vi", "lá số"]).passed

    def test_khong_yeu_cau_thi_dat(self):
        assert checks.kiem_co_it_nhat_mot("bất kỳ", []).passed

    def test_phai_co_du_moi_cum(self):
        assert checks.kiem_co_du("Cà Phê ABC ngon", ["Cà Phê ABC"]).passed
        r = checks.kiem_co_du("Cà phê ngon", ["Cà Phê ABC", "rang mộc"])
        assert not r.passed
        assert "rang mộc" in r.detail

    @pytest.mark.parametrize(
        "text,min_w,max_w,dat",
        [
            ("một hai ba bốn năm", 3, 10, True),
            ("một hai", 3, 10, False),
            ("một hai ba bốn năm sáu bảy tám chín mười mười một", 3, 10, False),
            ("một hai", None, None, True),
        ],
    )
    def test_do_dai(self, text, min_w, max_w, dat):
        assert checks.kiem_do_dai(text, min_w, max_w).passed is dat


class TestChayCaBo:
    def test_gom_du_cac_phep_kiem_context(self):
        ctx = {"loaded_docs": ["brand:identity"], "product_evidence": True}
        expect = {
            "retrieval": {
                "must_load": ["brand:identity"],
                "must_not_load": ["product:sai"],
                "product_evidence": True,
            }
        }
        ket_qua = checks.chay_kiem_retrieval(ctx, expect)

        assert len(ket_qua) == 3
        assert checks.tom_tat(ket_qua)["ok"]

    def test_khong_khai_bao_gi_thi_khong_kiem_gi(self):
        """
        Case không có kỳ vọng cho tầng này phải ra 0 phép kiểm — runner sẽ hiện
        SKIP. Trả về "đạt" ở đây là nói dối rằng nó đã được kiểm.
        """
        assert checks.chay_kiem_retrieval({}, {}) == []
        assert checks.tom_tat([])["total"] == 0

    def test_tom_tat_liet_ke_phep_kiem_truot(self):
        ket_qua = [
            checks.CheckResult("a", True),
            checks.CheckResult("b", False),
            checks.CheckResult("c", False),
        ]
        tt = checks.tom_tat(ket_qua)

        assert tt["passed"] == 1
        assert tt["total"] == 3
        assert not tt["ok"]
        assert tt["failed"] == ["b", "c"]


class TestCaseThat:
    """Bộ case trong repo phải hợp lệ — sai schema thì eval im lặng bỏ qua."""

    def test_moi_case_deu_doc_duoc(self):
        from evals.runner import nap_cases

        cases = nap_cases()
        assert cases, "không tìm thấy case nào"

        for c in cases:
            assert c.get("id"), f"{c.get('_file')}: thiếu id"
            assert c.get("description"), f"{c['id']}: thiếu description"
            assert c.get("brief", {}).get("raw_input"), f"{c['id']}: thiếu brief.raw_input"
            assert c.get("expect"), f"{c['id']}: thiếu expect"

    def test_id_khong_trung_nhau(self):
        from evals.runner import nap_cases

        ids = [c["id"] for c in nap_cases()]
        assert len(ids) == len(set(ids))

    def test_brand_duoc_tham_chieu_phai_ton_tai(self):
        from evals.runner import BRANDS_DIR, nap_cases

        for c in nap_cases():
            if c.get("brand"):
                assert (BRANDS_DIR / c["brand"]).is_dir(), f"{c['id']}: thiếu brand {c['brand']}"
