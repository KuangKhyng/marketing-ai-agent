"""
Roadmap mục 12 — truy nguồn từng khẳng định.

Reviewer cũ chấm `factuality = 0.92` và dừng. Con số đó không cho người duyệt
biết CÂU NÀO phải kiểm lại, nên thực tế chẳng ai kiểm gì.

Giờ mỗi khẳng định phải chỉ ra tài liệu chống lưng (id lấy từ thẻ
`<knowledge_document>` mà retriever bọc). Không chỉ được thì UNSUPPORTED, và đó
là vi phạm quy tắc cứng ở chiều factuality — chặn được kể cả khi LLM tự chấm
điểm cao.
"""
import pytest

import src.nodes.formatter as fm
from src.models.review import (
    ClaimStatus,
    ClaimVerification,
    LLMDimensionScore,
    LLMReviewOutput,
    ReviewDimension,
)
from src.nodes.reviewer import THRESHOLDS, _combine_results


def diem_cao_het():
    """LLM chấm cao ở mọi chiều — để chứng minh claim vẫn chặn được."""
    return [
        LLMDimensionScore(dimension=d, score=0.98, feedback="rất tốt")
        for d in ReviewDimension
    ]


def factuality(result):
    return next(
        ds for ds in result.dimension_scores if ds.dimension is ReviewDimension.FACTUALITY
    )


class TestChanKhangDinhKhongCoChoDua:
    def test_unsupported_lam_truot_factuality_du_diem_cao(self):
        llm = LLMReviewOutput(
            dimension_scores=diem_cao_het(),
            claims=[
                ClaimVerification(
                    claim="Được hơn 10.000 khách hàng tin dùng",
                    evidence_ids=[],
                    status=ClaimStatus.UNSUPPORTED,
                    note="Không tài liệu nào nhắc tới số khách",
                )
            ],
        )
        r = _combine_results([], llm)
        f = factuality(r)

        assert f.score >= THRESHOLDS[ReviewDimension.FACTUALITY], "LLM vẫn chấm cao"
        assert not f.passed, "điểm cao không được che một khẳng định không có chỗ dựa"
        assert not r.overall_passed
        assert any("10.000 khách" in v for v in f.rule_violations)

    def test_contradicted_noi_ro_la_nguoc(self):
        llm = LLMReviewOutput(
            dimension_scores=diem_cao_het(),
            claims=[
                ClaimVerification(
                    claim="Trả kết quả trong 2 giờ",
                    evidence_ids=["product/goi_xem_la_so"],
                    status=ClaimStatus.CONTRADICTED,
                    note="Tài liệu ghi 48 giờ",
                )
            ],
        )
        r = _combine_results([], llm)
        vi_pham = factuality(r).rule_violations

        assert any("NGƯỢC LẠI" in v for v in vi_pham)
        assert any("48 giờ" in v for v in vi_pham), "phải kèm lý do để người duyệt kiểm được"

    def test_noi_supported_nhung_khong_dua_ra_nguon_van_bi_chan(self):
        """
        Chỗ dễ lọt nhất: LLM đánh 'supported' cho có mà không chỉ ra tài liệu
        nào. Không có evidence_ids thì không phải là có chỗ dựa.
        """
        llm = LLMReviewOutput(
            dimension_scores=diem_cao_het(),
            claims=[
                ClaimVerification(
                    claim="Sản phẩm đạt chuẩn quốc tế",
                    evidence_ids=[],
                    status=ClaimStatus.SUPPORTED,
                )
            ],
        )
        assert not factuality(_combine_results([], llm)).passed

    def test_moi_khang_dinh_deu_co_cho_dua_thi_dat(self):
        llm = LLMReviewOutput(
            dimension_scores=diem_cao_het(),
            claims=[
                ClaimVerification(
                    claim="Trả kết quả trong 48 giờ",
                    evidence_ids=["product/goi_xem_la_so"],
                    status=ClaimStatus.SUPPORTED,
                ),
                ClaimVerification(
                    claim="Giá 500.000đ",
                    evidence_ids=["product/goi_xem_la_so"],
                    status=ClaimStatus.SUPPORTED,
                ),
            ],
        )
        r = _combine_results([], llm)

        assert r.overall_passed
        assert len(r.claims) == 2

    def test_khong_co_claim_nao_thi_khong_anh_huong(self):
        """Bài không khẳng định gì (thuần cảm xúc) là hợp lệ."""
        r = _combine_results([], LLMReviewOutput(dimension_scores=diem_cao_het(), claims=[]))
        assert r.overall_passed

    def test_claim_di_ra_toi_ket_qua(self):
        llm = LLMReviewOutput(
            dimension_scores=diem_cao_het(),
            claims=[
                ClaimVerification(claim="X", evidence_ids=["a"], status=ClaimStatus.SUPPORTED)
            ],
        )
        r = _combine_results([], llm)

        assert r.claims[0].claim == "X"
        assert r.claims[0].evidence_ids == ["a"]


class TestFileBanGiao:
    """Người cầm file phải biết câu nào cần kiểm lại."""

    def _md(self, claims):
        from test_formatter import a_brief, a_piece, a_review
        from src.models.content import CampaignContent
        from src.models.trace import RunTrace

        review = a_review()
        review.claims = claims
        return fm._build_markdown(
            CampaignContent(pieces=[a_piece()], master_message_summary="x"),
            a_brief(), review, RunTrace(),
        )

    def test_hien_bang_truy_nguon(self):
        md = self._md([
            ClaimVerification(
                claim="Trả trong 48 giờ",
                evidence_ids=["product/goi_xem_la_so"],
                status=ClaimStatus.SUPPORTED,
            ),
            ClaimVerification(
                claim="10.000 khách tin dùng", evidence_ids=[], status=ClaimStatus.UNSUPPORTED
            ),
        ])

        assert "Truy nguồn khẳng định (1/2 có chỗ dựa)" in md
        assert "product/goi_xem_la_so" in md
        assert "KHÔNG có chỗ dựa" in md
        assert "cần người kiểm lại trước khi đăng" in md

    def test_khong_co_claim_thi_khong_hien_bang(self):
        assert "Truy nguồn khẳng định" not in self._md([])

    def test_dau_gach_dung_trong_claim_khong_lam_vo_bang(self):
        md = self._md([
            ClaimVerification(claim="Giá 500k | giảm còn 400k", evidence_ids=[],
                              status=ClaimStatus.UNSUPPORTED)
        ])
        dong = [d for d in md.splitlines() if "500k" in d][0]
        assert "\\|" in dong, "dấu gạch trong nội dung phải được escape, nếu không bảng vỡ"
        # 3 ô -> 4 dấu phân cách, cộng 1 dấu đã escape nằm trong nội dung
        assert dong.count("|") == 5
