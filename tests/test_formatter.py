"""
F3 — formatter: thứ khách hàng thật sự nhận.

UI đẹp đến mấy cũng chỉ là màn hình; `outputs/{run_id}/content.md` mới là cái
được gửi đi và lưu lại. Nó phải nói đúng và đủ như UI, nhất là phần chấm chất
lượng — người cầm file không nhìn thấy màn hình.
"""
import json

import pytest

import src.nodes.formatter as fm
from src.models.brief import (
    AudienceSpec,
    BrandSpec,
    CampaignBrief,
    CampaignGoal,
    Channel,
    Deliverable,
    OfferSpec,
)
from src.models.content import CampaignContent, ContentPiece
from src.models.review import DimensionScore, ReviewDimension, ReviewResult
from src.models.trace import RunTrace


@pytest.fixture
def outputs(tmp_path, monkeypatch):
    d = tmp_path / "outputs"
    monkeypatch.setattr(fm, "OUTPUTS_DIR", d)
    return d


def a_brief():
    return CampaignBrief(
        goal=CampaignGoal.AWARENESS,
        brand=BrandSpec(name="Cà Phê ABC"),
        audience=AudienceSpec(persona_description="dân văn phòng"),
        offer=OfferSpec(product_or_service="cà phê rang mộc", key_message="tươi", cta="ghé quán"),
        channels=[Channel.FACEBOOK, Channel.TIKTOK],
        deliverables=[Deliverable.POST],
    )


def a_piece(channel=Channel.FACEBOOK, **kw):
    base = dict(
        channel=channel,
        deliverable=Deliverable.POST,
        body="Sáng nay mẻ đầu vừa ra lò.",
        cta_text="Ghé quán thử",
        hashtags=["#caphe"],
        word_count=6,
    )
    base.update(kw)
    return ContentPiece(**base)


def a_review(passed=True, violations=None, unavailable=False, issues=None):
    return ReviewResult(
        overall_passed=passed,
        review_unavailable=unavailable,
        dimension_scores=[
            DimensionScore(
                dimension=d,
                score=0.9 if passed else 0.4,
                passed=passed,
                feedback="ok" if passed else "chưa đạt",
                rule_violations=violations or [] if d is ReviewDimension.BRAND_FIT else [],
            )
            for d in ReviewDimension
        ],
        critical_issues=issues or [],
    )


def a_state(content=None, review=None):
    return {
        "campaign_content": content or CampaignContent(
            pieces=[a_piece()], master_message_summary="Rang mỗi ngày"
        ),
        "brief": a_brief(),
        "review_result": review if review is not None else a_review(),
        "trace": RunTrace(),
    }


# === Nội dung bàn giao ===


class TestMarkdown:
    def test_co_du_cac_phan_cua_mot_bai(self, outputs):
        piece = a_piece(headline="Tiêu đề", hook="Câu mở", visual_direction="Ảnh mẻ rang",
                        notes="Đăng 7h sáng")
        md = fm._build_markdown(
            CampaignContent(pieces=[piece], master_message_summary="tóm tắt"),
            a_brief(), a_review(), RunTrace(),
        )

        for phan in ("Tiêu đề", "Câu mở", "Sáng nay mẻ đầu", "Ghé quán thử",
                     "#caphe", "Ảnh mẻ rang", "Đăng 7h sáng"):
            assert phan in md, f"thiếu {phan}"

    def test_khong_in_truong_rong(self, outputs):
        """Không được ra '**Headline:** None' trong file gửi khách."""
        md = fm._build_markdown(
            CampaignContent(pieces=[a_piece()], master_message_summary="x"),
            a_brief(), a_review(), RunTrace(),
        )
        assert "None" not in md
        assert "Headline" not in md

    def test_nhom_theo_kenh(self, outputs):
        content = CampaignContent(
            pieces=[a_piece(Channel.FACEBOOK), a_piece(Channel.TIKTOK)],
            master_message_summary="x",
        )
        md = fm._build_markdown(content, a_brief(), a_review(), RunTrace())

        assert "## FACEBOOK" in md
        assert "## TIKTOK" in md

    def test_co_bang_diem(self, outputs):
        md = fm._build_markdown(
            CampaignContent(pieces=[a_piece()], master_message_summary="x"),
            a_brief(), a_review(), RunTrace(),
        )
        for chieu in ReviewDimension:
            assert chieu.value in md
        assert "PASSED" in md


class TestBanGiaoPhaiTrungThuc:
    """
    Phần chấm trong file phải nói đủ như UI. Người cầm file không nhìn thấy
    màn hình, nên giấu bớt ở đây là để họ bàn giao nhầm.
    """

    def test_hien_vi_pham_quy_tac_cung(self, outputs):
        review = a_review(
            passed=False,
            violations=["[facebook/post] Missing mandatory brand term: 'Cà Phê ABC'"],
        )
        md = fm._build_markdown(
            CampaignContent(pieces=[a_piece()], master_message_summary="x"),
            a_brief(), review, RunTrace(),
        )

        assert "Missing mandatory brand term" in md, (
            "vi phạm quy tắc cứng làm chiều đó trượt — không hiện ra thì người "
            "đọc file không hiểu vì sao trượt"
        )

    def test_hien_van_de_phat_hien_duoc(self, outputs):
        review = a_review(passed=False, issues=["[facebook/post] Too long: 900 words (max: 300)"])
        md = fm._build_markdown(
            CampaignContent(pieces=[a_piece()], master_message_summary="x"),
            a_brief(), review, RunTrace(),
        )
        assert "Too long: 900 words" in md

    def test_noi_ro_khi_chua_cham_duoc(self, outputs):
        """"Chưa kiểm được" khác hoàn toàn với "đã kiểm và trượt"."""
        review = a_review(passed=False, unavailable=True)
        md = fm._build_markdown(
            CampaignContent(pieces=[a_piece()], master_message_summary="x"),
            a_brief(), review, RunTrace(),
        )

        assert "CHƯA KIỂM" in md.upper() or "CHƯA CHẤM" in md.upper(), (
            "reviewer lỗi mà file chỉ ghi FAILED thì người đọc tưởng nội dung đã được kiểm"
        )


# === JSON ===


class TestJson:
    def test_co_du_brief_content_review(self, outputs):
        out = fm._build_json(
            CampaignContent(pieces=[a_piece()], master_message_summary="x"),
            a_brief(), a_review(), RunTrace(),
        )

        assert out["brief"]["offer"]["product_or_service"] == "cà phê rang mộc"
        assert out["content"]["pieces"][0]["body"].startswith("Sáng nay")
        assert out["review"]["overall_passed"] is True
        assert "cost_estimate" in out["trace_summary"]

    def test_khong_co_review_van_dung_duoc(self, outputs):
        out = fm._build_json(
            CampaignContent(pieces=[a_piece()], master_message_summary="x"),
            a_brief(), None, RunTrace(),
        )
        assert out["review"] is None


# === Ghi file ===


class TestGhiFile:
    def test_ghi_du_ba_file(self, outputs, monkeypatch):
        monkeypatch.setattr(fm, "_print_console_output", lambda *a, **k: None)
        state = a_state()

        out = fm.formatter_node(state)
        run_dir = outputs / out["trace"].run_id

        assert (run_dir / "content.md").exists()
        assert (run_dir / "content.json").exists()
        assert (run_dir / "trace.json").exists()

    def test_danh_dau_hoan_tat_trong_trace(self, outputs, monkeypatch):
        monkeypatch.setattr(fm, "_print_console_output", lambda *a, **k: None)
        out = fm.formatter_node(a_state())

        assert out["trace"].final_status == "completed"
        assert out["trace"].finished_at is not None
        assert "cà phê rang mộc" in out["trace"].brief_summary

    def test_trace_json_khop_trang_thai_cuoi(self, outputs, monkeypatch):
        """/campaigns/history đọc file này — ghi trước rồi mới hoàn tất là sai."""
        monkeypatch.setattr(fm, "_print_console_output", lambda *a, **k: None)
        out = fm.formatter_node(a_state())

        trace_file = outputs / out["trace"].run_id / "trace.json"
        data = json.loads(trace_file.read_text(encoding="utf-8"))
        assert data["final_status"] == "completed"

    def test_node_truoc_loi_thi_khong_ghi_gi(self, outputs):
        state = a_state()
        state["error"] = "channel_renderer hỏng"

        out = fm.formatter_node(state)

        assert out["current_node"] == "formatter"
        assert not outputs.exists(), "pipeline đã lỗi thì không được xuất bản gì"


# === R6: node không được in nội dung ra stdout ===


def test_khong_in_noi_dung_ra_stdout(outputs, capsys):
    """
    Web API dùng chung node này, mà log server đi stdout. In ra là đẩy nguyên
    campaign chưa công bố của khách vào log nền tảng (Railway/container).
    """
    fm.formatter_node(a_state())

    ra = capsys.readouterr()
    assert "Sáng nay mẻ đầu" not in ra.out, "nội dung campaign lọt vào stdout"
    assert "Ghé quán thử" not in ra.out


def test_cli_van_in_duoc_khi_can(outputs, capsys):
    """CLI vẫn phải xem được kết quả — chỉ là phải tự gọi."""
    state = a_state()
    fm.formatter_node(state)

    fm.print_console_output(state)

    ra = capsys.readouterr()
    assert "Sáng nay mẻ đầu" in ra.out
