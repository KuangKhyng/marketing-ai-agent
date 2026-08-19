"""
Các phép chấm cho eval case.

Nguyên tắc: **ưu tiên phép kiểm xác định**. Một `assert "cải mệnh" not in text`
cho câu trả lời như nhau mọi lúc, ai đọc cũng hiểu vì sao trượt, và không tốn
tiền. Chỉ dùng LLM chấm khi thật sự không có cách nào kiểm bằng code — và khi
đó phải ghi rõ là điểm chủ quan.

Mỗi phép kiểm trả về CheckResult chứ không raise: một case cần chạy hết mọi
phép kiểm để biết nó hỏng ở bao nhiêu chỗ, không phải dừng ở chỗ đầu tiên.
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    # Thông tin thêm để so hai lần chạy, không dùng để chấm đỗ/trượt
    meta: dict = field(default_factory=dict)


def _chuan_hoa(text: str) -> str:
    return " ".join((text or "").lower().split())


# === Kiểm context (tầng retrieval — không tốn tiền) ===


def kiem_da_nap(context_pack: dict, must_load: list[str]) -> CheckResult:
    """Những tài liệu BẮT BUỘC phải có mặt trong context."""
    da_nap = set(context_pack.get("loaded_docs") or [])
    thieu = [d for d in must_load if d not in da_nap]
    return CheckResult(
        name="must_load",
        passed=not thieu,
        detail=f"thiếu: {', '.join(thieu)}" if thieu else "đủ",
        meta={"loaded": sorted(da_nap)},
    )


def kiem_khong_nap(context_pack: dict, must_not_load: list[str]) -> CheckResult:
    """
    Những tài liệu KHÔNG được có mặt.

    Đây là phép kiểm bắt được lỗi retriever lấy bừa: brief về kem chống nắng mà
    context lại chứa serum trị mụn.
    """
    da_nap = set(context_pack.get("loaded_docs") or [])
    thua = [d for d in must_not_load if d in da_nap]
    return CheckResult(
        name="must_not_load",
        passed=not thua,
        detail=f"nạp nhầm: {', '.join(thua)}" if thua else "sạch",
    )


def kiem_bang_chung(context_pack: dict, mong_doi: bool) -> CheckResult:
    """
    Có tra được tài liệu sản phẩm thật không.

    False nghĩa là hệ thống phải tự nhận "tôi không có bằng chứng" thay vì lấy
    bừa một file khác — xem R5.
    """
    that = bool(context_pack.get("product_evidence"))
    return CheckResult(
        name="product_evidence",
        passed=that == mong_doi,
        detail=f"mong đợi {mong_doi}, thực tế {that}",
    )


# === Kiểm nội dung sinh ra (tầng generation — tốn tiền) ===


def kiem_khong_chua(text: str, cam: list[str]) -> CheckResult:
    """
    Những cụm TUYỆT ĐỐI không được xuất hiện.

    Đây là phép kiểm giá trị nhất của cả bộ eval: nó mã hoá ràng buộc pháp lý
    và cam kết brand thành thứ kiểm được, thay vì hy vọng reviewer bắt được.
    """
    thap = _chuan_hoa(text)
    vi_pham = [c for c in cam if _chuan_hoa(c) in thap]
    return CheckResult(
        name="must_not_contain",
        passed=not vi_pham,
        detail=f"chứa: {', '.join(vi_pham)}" if vi_pham else "sạch",
    )


def kiem_co_it_nhat_mot(text: str, can: list[str]) -> CheckResult:
    """Ít nhất một trong các cụm phải xuất hiện — bài phải nói đúng chủ đề."""
    if not can:
        return CheckResult(name="must_contain_any", passed=True, detail="không yêu cầu")
    thap = _chuan_hoa(text)
    thay = [c for c in can if _chuan_hoa(c) in thap]
    return CheckResult(
        name="must_contain_any",
        passed=bool(thay),
        detail=f"thấy: {', '.join(thay)}" if thay else f"không thấy cụm nào trong {can}",
    )


def kiem_co_du(text: str, bat_buoc: list[str]) -> CheckResult:
    """Mọi cụm đều phải xuất hiện — dùng cho mandatory_terms."""
    thap = _chuan_hoa(text)
    thieu = [c for c in bat_buoc if _chuan_hoa(c) not in thap]
    return CheckResult(
        name="must_contain_all",
        passed=not thieu,
        detail=f"thiếu: {', '.join(thieu)}" if thieu else "đủ",
    )


def kiem_do_dai(text: str, min_words: Optional[int], max_words: Optional[int]) -> CheckResult:
    so_tu = len((text or "").split())
    loi = []
    if min_words and so_tu < min_words:
        loi.append(f"quá ngắn ({so_tu} < {min_words})")
    if max_words and so_tu > max_words:
        loi.append(f"quá dài ({so_tu} > {max_words})")
    return CheckResult(
        name="word_count",
        passed=not loi,
        detail="; ".join(loi) if loi else f"{so_tu} từ",
        meta={"words": so_tu},
    )


def kiem_khong_bia_khi_thieu_bang_chung(text: str, dau_hieu_bia: list[str]) -> CheckResult:
    """
    Khi không có tài liệu sản phẩm, bài không được khẳng định chi tiết cụ thể.

    Không có cách kiểm hoàn hảo bằng code, nên dùng các dấu hiệu dễ nhận: con
    số cụ thể, cụm cam kết, tên thành phần. Trượt ở đây là tín hiệu cần đọc
    bằng mắt, không phải kết luận chắc chắn.
    """
    return CheckResult(
        name="abstain",
        passed=kiem_khong_chua(text, dau_hieu_bia).passed,
        detail=kiem_khong_chua(text, dau_hieu_bia).detail,
    )


def kiem_moi_khang_dinh_co_cho_dua(review_result) -> CheckResult:
    """
    Mọi khẳng định trong bài đều phải chỉ ra được tài liệu chống lưng.

    Đây là phép kiểm khác hẳn về chất so với "factuality >= 0.9": nó nêu tên
    từng câu không có chỗ dựa, nên người đọc báo cáo biết phải kiểm lại cái gì.
    """
    claims = list(getattr(review_result, "claims", None) or [])
    if not claims:
        return CheckResult(
            name="claims_all_supported",
            passed=True,
            detail="bài không có khẳng định nào về sự thật",
        )

    treo = [c for c in claims if getattr(c.status, "value", c.status) != "supported"]
    return CheckResult(
        name="claims_all_supported",
        passed=not treo,
        detail=(
            "không có chỗ dựa: " + "; ".join(c.claim[:50] for c in treo)
            if treo
            else f"{len(claims)}/{len(claims)} có chỗ dựa"
        ),
        meta={"total": len(claims), "unsupported": len(treo)},
    )


# === Chấm một case ===


def chay_kiem_retrieval(context_pack: dict, expect: dict) -> list[CheckResult]:
    ket_qua = []
    r = expect.get("retrieval") or {}

    if "must_load" in r:
        ket_qua.append(kiem_da_nap(context_pack, r["must_load"]))
    if "must_not_load" in r:
        ket_qua.append(kiem_khong_nap(context_pack, r["must_not_load"]))
    if "product_evidence" in r:
        ket_qua.append(kiem_bang_chung(context_pack, r["product_evidence"]))

    return ket_qua


def chay_kiem_noi_dung(text: str, expect: dict, review_result=None) -> list[CheckResult]:
    ket_qua = []
    c = expect.get("content") or {}

    if (expect.get("claims") or {}).get("all_supported") and review_result is not None:
        ket_qua.append(kiem_moi_khang_dinh_co_cho_dua(review_result))

    if c.get("must_not_contain"):
        ket_qua.append(kiem_khong_chua(text, c["must_not_contain"]))
    if c.get("must_contain_any"):
        ket_qua.append(kiem_co_it_nhat_mot(text, c["must_contain_any"]))
    if c.get("must_contain_all"):
        ket_qua.append(kiem_co_du(text, c["must_contain_all"]))
    if c.get("min_words") or c.get("max_words"):
        ket_qua.append(kiem_do_dai(text, c.get("min_words"), c.get("max_words")))
    if c.get("abstain_signals"):
        ket_qua.append(kiem_khong_bia_khi_thieu_bang_chung(text, c["abstain_signals"]))

    return ket_qua


def tom_tat(ket_qua: list[CheckResult]) -> dict[str, Any]:
    dat = sum(1 for r in ket_qua if r.passed)
    return {
        "passed": dat,
        "total": len(ket_qua),
        "ok": dat == len(ket_qua),
        "failed": [r.name for r in ket_qua if not r.passed],
    }
