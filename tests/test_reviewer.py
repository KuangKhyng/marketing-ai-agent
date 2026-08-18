"""
G2 + G3 — reviewer.

  A3: reviewer lỗi phải fail-closed, không được hiện ra như "đã đạt"
  A5: LLM trả thiếu/trùng dimension không được trôi thành "đạt"
  A4: vi phạm quy tắc cứng phải làm chiều đó trượt, và phải hiện ra được
"""
import pytest

from src.models.review import (
    LLMDimensionScore,
    LLMReviewOutput,
    ReviewDimension,
)
from src.nodes import reviewer as reviewer_mod
from src.nodes.reviewer import THRESHOLDS, _combine_results, _run_rule_checks, reviewer_node


def diem_dat_het():
    """Điểm LLM vượt ngưỡng ở cả 5 chiều."""
    return LLMReviewOutput(
        dimension_scores=[
            LLMDimensionScore(dimension=d, score=0.95, feedback="ổn")
            for d in ReviewDimension
        ]
    )


# === A3: reviewer lỗi => fail-closed ===


def test_reviewer_loi_thi_khong_ket_luan_la_dat(review_state, monkeypatch):
    def no_len(*args, **kwargs):
        raise RuntimeError("rate limited")

    monkeypatch.setattr(reviewer_mod, "_run_llm_review", no_len)

    out = reviewer_node(review_state)
    result = out["review_result"]

    assert result.overall_passed is False, "Reviewer lỗi mà vẫn báo đạt là fail-open"
    assert result.review_unavailable is True
    assert all(not ds.passed for ds in result.dimension_scores)
    assert any("CHƯA được kiểm" in issue for issue in result.critical_issues)


def test_reviewer_loi_van_tang_revision_count(review_state, monkeypatch):
    """Không tăng thì nhánh LangGraph retry vô hạn khi reviewer lỗi liên tục."""
    monkeypatch.setattr(
        reviewer_mod, "_run_llm_review", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
    )
    out = reviewer_node(review_state)
    assert out["revision_count"] == 1


# === A5: dimension thiếu / trùng ===


def test_thieu_dimension_thi_chieu_do_truot():
    llm = LLMReviewOutput(
        dimension_scores=[
            LLMDimensionScore(dimension=d, score=0.95, feedback="ổn")
            for d in ReviewDimension
            if d is not ReviewDimension.CONTENT_DEPTH
        ]
    )
    result = _combine_results([], llm)

    assert len(result.dimension_scores) == 5, "Phải luôn trả đủ 5 chiều"
    thieu = next(
        ds for ds in result.dimension_scores if ds.dimension is ReviewDimension.CONTENT_DEPTH
    )
    assert thieu.passed is False
    assert result.overall_passed is False
    assert any("không chấm" in i for i in result.critical_issues)


def test_llm_tra_rong_thi_khong_pass():
    """all([]) là True — đây chính là chỗ trước đây trôi thành 'đạt'."""
    result = _combine_results([], LLMReviewOutput(dimension_scores=[]))
    assert result.overall_passed is False
    assert len(result.dimension_scores) == 5


def test_dimension_trung_thi_giu_diem_thap_nhat():
    llm = LLMReviewOutput(
        dimension_scores=[
            LLMDimensionScore(dimension=ReviewDimension.BRAND_FIT, score=0.95, feedback="cao"),
            LLMDimensionScore(dimension=ReviewDimension.BRAND_FIT, score=0.20, feedback="thấp"),
        ]
        + [
            LLMDimensionScore(dimension=d, score=0.95, feedback="ổn")
            for d in ReviewDimension
            if d is not ReviewDimension.BRAND_FIT
        ]
    )
    result = _combine_results([], llm)
    brand = next(
        ds for ds in result.dimension_scores if ds.dimension is ReviewDimension.BRAND_FIT
    )
    assert brand.score == pytest.approx(0.20)
    assert brand.passed is False


def test_diem_dat_het_thi_pass():
    """Kiểm tra chiều ngược lại — fix không được làm mọi thứ luôn trượt."""
    result = _combine_results([], diem_dat_het())
    assert result.overall_passed is True
    assert result.revision_instructions is None
    assert result.review_unavailable is False


# === A4: rule check phải có tác dụng ===


def test_vi_pham_quy_tac_cung_lam_truot_du_diem_cao():
    rule_issues = [(ReviewDimension.BRAND_FIT, "[facebook/post] Missing mandatory brand term: 'ABC'")]
    result = _combine_results(rule_issues, diem_dat_het())

    brand = next(
        ds for ds in result.dimension_scores if ds.dimension is ReviewDimension.BRAND_FIT
    )
    assert brand.score >= THRESHOLDS[ReviewDimension.BRAND_FIT]
    assert brand.passed is False, "Điểm cao không được che vi phạm quy tắc cứng"
    assert brand.rule_violations == [rule_issues[0][1]]
    assert result.overall_passed is False


def test_vi_pham_chi_lam_truot_dung_chieu_cua_no():
    rule_issues = [(ReviewDimension.BRAND_FIT, "[facebook/post] Missing mandatory brand term: 'ABC'")]
    result = _combine_results(rule_issues, diem_dat_het())

    khac = [
        ds for ds in result.dimension_scores if ds.dimension is not ReviewDimension.BRAND_FIT
    ]
    assert all(ds.passed for ds in khac)
    assert all(ds.rule_violations == [] for ds in khac)


def test_vi_pham_hien_ra_duoc_cho_user():
    """Trước đây rule issue được tính rồi không hiện ở đâu cả."""
    rule_issues = [(ReviewDimension.CHANNEL_FIT, "[facebook/post] Too long: 900 words (max: 300)")]
    result = _combine_results(rule_issues, diem_dat_het())

    assert "[facebook/post] Too long: 900 words (max: 300)" in result.critical_issues
    assert "Too long" in result.revision_instructions


# === rule check gắn đúng dimension ===


def test_thieu_mandatory_term_gan_vao_brand_fit(brief, content):
    brief.brand.mandatory_terms = ["Cà Phê ABC"]
    issues = _run_rule_checks(content, brief, {})

    assert issues, "Body không chứa mandatory term nên phải có vi phạm"
    assert any(
        dim is ReviewDimension.BRAND_FIT and "mandatory brand term" in msg
        for dim, msg in issues
    )


def test_vuot_word_limit_gan_vao_channel_fit(brief, content):
    brief.constraints.word_limit = 10
    issues = _run_rule_checks(content, brief, {})

    assert any(
        dim is ReviewDimension.CHANNEL_FIT and "exceeds limit" in msg for dim, msg in issues
    )


def test_forbidden_claim_gan_vao_factuality(brief, content):
    brief.brand.forbidden_claims = ["rang một mẻ nhỏ"]
    issues = _run_rule_checks(content, brief, {})

    assert any(
        dim is ReviewDimension.FACTUALITY and "forbidden brand claim" in msg
        for dim, msg in issues
    )


def test_khong_vi_pham_thi_khong_co_issue(brief, content):
    assert _run_rule_checks(content, brief, {}) == []
