"""
Mọi kiểu trong CampaignState phải khôi phục lại đúng class của nó.

Vì sao cần canh: `_ALLOWED_CHECKPOINT_TYPES` trong src/graph/workflow.py quyết
định kiểu nào được dựng lại từ checkpoint. Kiểu THIẾU trong danh sách đó không
báo lỗi gì cả — LangGraph lặng lẽ trả về `dict` thay vì object. Pipeline sau đó
gọi `trace.node_traces.append(...)` trên một dict rồi vỡ ở chỗ hoàn toàn khác,
rất khó truy ngược về đây.

Nên: thêm model mới vào state mà quên khai báo thì test này đỏ ngay.
"""
from datetime import datetime

import pytest

from src.graph.workflow import _build_serializer
from src.models.brief import (
    AudienceSpec,
    BrandSpec,
    CampaignBrief,
    CampaignGoal,
    Channel,
    ContentConstraints,
    Deliverable,
    OfferSpec,
    SuccessCriteria,
)
from src.models.content import CampaignContent, ContentPiece
from src.models.message import MasterMessage
from src.models.review import DimensionScore, ReviewDimension, ReviewResult
from src.models.trace import NodeTrace, RunTrace


def _brief():
    return CampaignBrief(
        goal=CampaignGoal.AWARENESS,
        brand=BrandSpec(name="Cà Phê ABC"),
        audience=AudienceSpec(persona_description="Dân công sở"),
        offer=OfferSpec(product_or_service="Cà phê", key_message="Tươi", cta="Ghé quán"),
        channels=[Channel.FACEBOOK],
        deliverables=[Deliverable.POST],
    )


def _piece():
    return ContentPiece(
        channel=Channel.FACEBOOK, deliverable=Deliverable.POST, body="x " * 50, word_count=50
    )


MOI_KIEU_TRONG_STATE = [
    RunTrace(),
    NodeTrace(node_name="reviewer", started_at=datetime.now()),
    _brief(),
    BrandSpec(name="X"),
    AudienceSpec(persona_description="Y"),
    OfferSpec(product_or_service="A", key_message="B", cta="C"),
    ContentConstraints(),
    SuccessCriteria(),
    MasterMessage(core_promise="Hứa", key_points=["một"]),
    CampaignContent(pieces=[_piece()], master_message_summary="tóm tắt"),
    _piece(),
    ReviewResult(
        overall_passed=True,
        dimension_scores=[
            DimensionScore(dimension=d, score=0.9, passed=True, feedback="ok")
            for d in ReviewDimension
        ],
    ),
]


@pytest.mark.parametrize("obj", MOI_KIEU_TRONG_STATE, ids=lambda o: type(o).__name__)
def test_round_trip_giu_dung_class(obj):
    ser = _build_serializer()
    khoi_phuc = ser.loads_typed(ser.dumps_typed(obj))

    assert type(khoi_phuc) is type(obj), (
        f"{type(obj).__name__} bị hạ thành {type(khoi_phuc).__name__} — "
        "thêm nó vào _ALLOWED_CHECKPOINT_TYPES trong src/graph/workflow.py"
    )


def test_kieu_long_nhau_cung_giu_dung_class():
    """Model lồng trong model cũng phải dựng lại đúng, không chỉ lớp ngoài."""
    ser = _build_serializer()
    brief = ser.loads_typed(ser.dumps_typed(_brief()))

    assert isinstance(brief.brand, BrandSpec)
    assert isinstance(brief.audience, AudienceSpec)
    assert isinstance(brief.offer, OfferSpec)
    assert brief.goal is CampaignGoal.AWARENESS
    assert brief.channels == [Channel.FACEBOOK]


def test_kieu_la_bi_ha_thanh_dict():
    """
    Chốt hành vi mà test trên dựa vào: KHÔNG có ngoại lệ nào được ném ra, kiểu
    lạ chỉ bị hạ xuống dict. Nếu LangGraph đổi sang raise thì test này đỏ và
    cần xem lại cách chặn.
    """
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    ser_hep = JsonPlusSerializer(allowed_msgpack_modules=[("src.models.brief", "BrandSpec")])
    ra = ser_hep.loads_typed(ser_hep.dumps_typed(RunTrace()))

    assert isinstance(ra, dict)
    assert "run_id" in ra
