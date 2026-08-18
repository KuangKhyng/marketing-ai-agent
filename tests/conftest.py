"""Fixtures dùng chung — không có test nào gọi Anthropic API thật."""
import pytest

from src.models.brief import (
    AudienceSpec,
    BrandSpec,
    CampaignBrief,
    CampaignGoal,
    Channel,
    ContentConstraints,
    Deliverable,
    OfferSpec,
)
from src.models.content import CampaignContent, ContentPiece
from src.models.message import MasterMessage
from src.models.trace import RunTrace


@pytest.fixture
def brief():
    return CampaignBrief(
        goal=CampaignGoal.AWARENESS,
        brand=BrandSpec(name="Cà Phê ABC"),
        audience=AudienceSpec(persona_description="Dân công sở 25-35"),
        offer=OfferSpec(
            product_or_service="Cà phê rang mộc",
            key_message="Rang nhỏ mỗi ngày",
            cta="Ghé quán thử",
        ),
        channels=[Channel.FACEBOOK],
        deliverables=[Deliverable.POST],
    )


@pytest.fixture
def piece():
    """
    Piece "sạch": nằm trong khoảng 150-600 từ mà platforms.yaml đặt cho
    facebook/post, hashtag lowercase, không trùng headline/hook — để test nào
    cố tình tạo vi phạm thì vi phạm đó là của chính nó.
    """
    body = "Sáng nào cũng rang một mẻ nhỏ, đủ bán trong ngày. " * 25
    return ContentPiece(
        channel=Channel.FACEBOOK,
        deliverable=Deliverable.POST,
        body=body,
        cta_text="Ghé quán thử",
        hashtags=["#caphe"],
        word_count=len(body.split()),
    )


@pytest.fixture
def content(piece):
    return CampaignContent(pieces=[piece], master_message_summary="Rang nhỏ mỗi ngày")


@pytest.fixture
def master_message():
    return MasterMessage(
        core_promise="Rang nhỏ mỗi ngày nên cà phê luôn tươi",
        key_points=["Rang theo ngày", "Không tồn kho"],
        emotional_angle="Tin cậy",
    )


@pytest.fixture
def review_state(brief, content, master_message):
    """State đủ để chạy reviewer_node."""
    return {
        "brief": brief,
        "campaign_content": content,
        "context_pack": {"voice_profile": {}, "product": "", "policies": ""},
        "master_message": master_message,
        "revision_count": 0,
        "max_revisions": 2,
        "trace": RunTrace(),
        "warnings": [],
    }
