"""
G4 — A6: render thất bại không được đi tiếp trong im lặng.

Trước đây tất cả piece fail vẫn trả về CampaignContent(pieces=[]) và UI hiện
màn duyệt nội dung trống trơn, không lỗi, không cảnh báo.
"""
from src.models.brief import Channel, Deliverable
from src.models.content import ContentPiece
from src.nodes import channel_renderer as cr
from src.nodes.channel_renderer import channel_renderer_node


def _piece(channel, deliverable):
    return ContentPiece(
        channel=channel,
        deliverable=deliverable,
        body="Nội dung mẫu " * 30,
        cta_text="Ghé quán",
        word_count=90,
    )


def _state(brief, master_message, channels, deliverables):
    brief.channels = channels
    brief.deliverables = deliverables
    return {
        "brief": brief,
        "master_message": master_message,
        "context_pack": {"voice_profile": {}, "platform_rules": {}, "policies": ""},
        "trace": None,
        "warnings": [],
    }


def test_tat_ca_piece_fail_thi_bao_loi(brief, master_message, monkeypatch):
    monkeypatch.setattr(cr, "_render_single_piece", lambda **kwargs: None)

    state = _state(brief, master_message, [Channel.FACEBOOK, Channel.TIKTOK],
                   [Deliverable.POST, Deliverable.SHORT_VIDEO_SCRIPT])
    out = channel_renderer_node(state)

    assert out.get("error"), "Không render được gì mà không báo lỗi là bug A6"
    assert "Không tạo được nội dung cho kênh nào" in out["error"]
    assert "campaign_content" not in out, "Không được trả về content rỗng như thể thành công"


def test_fail_mot_phan_thi_canh_bao_nhung_van_di_tiep(brief, master_message, monkeypatch):
    def render_one(channel, deliverable, **kwargs):
        # TikTok fail, Facebook ok
        if channel is Channel.TIKTOK:
            return None
        return _piece(channel, deliverable)

    monkeypatch.setattr(cr, "_render_single_piece", render_one)

    state = _state(brief, master_message, [Channel.FACEBOOK, Channel.TIKTOK],
                   [Deliverable.POST, Deliverable.SHORT_VIDEO_SCRIPT])
    out = channel_renderer_node(state)

    assert not out.get("error")
    assert len(out["campaign_content"].pieces) == 1
    assert len(out["warnings"]) == 1
    assert "tiktok/short_video_script" in out["warnings"][0]


def test_render_du_thi_khong_canh_bao(brief, master_message, monkeypatch):
    monkeypatch.setattr(
        cr,
        "_render_single_piece",
        lambda channel, deliverable, **kwargs: _piece(channel, deliverable),
    )

    state = _state(brief, master_message, [Channel.FACEBOOK], [Deliverable.POST])
    out = channel_renderer_node(state)

    assert not out.get("error")
    assert out["warnings"] == []
    assert len(out["campaign_content"].pieces) == 1


def test_canh_bao_cu_khong_bi_mat(brief, master_message, monkeypatch):
    """warnings tích luỹ, không ghi đè cảnh báo của bước trước."""
    monkeypatch.setattr(cr, "_render_single_piece", lambda **kwargs: None)

    state = _state(brief, master_message, [Channel.FACEBOOK], [Deliverable.POST])
    state["warnings"] = ["cảnh báo từ bước trước"]
    out = channel_renderer_node(state)
    # Trường hợp fail hết thì trả error, warnings giữ nguyên trong state cũ
    assert out.get("error")

    def render_one(channel, deliverable, **kwargs):
        return None if channel is Channel.TIKTOK else _piece(channel, deliverable)

    monkeypatch.setattr(cr, "_render_single_piece", render_one)
    state = _state(brief, master_message, [Channel.FACEBOOK, Channel.TIKTOK],
                   [Deliverable.POST, Deliverable.SHORT_VIDEO_SCRIPT])
    state["warnings"] = ["cảnh báo từ bước trước"]
    out = channel_renderer_node(state)

    assert out["warnings"][0] == "cảnh báo từ bước trước"
    assert len(out["warnings"]) == 2
