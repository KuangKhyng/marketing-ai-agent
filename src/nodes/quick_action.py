"""
Quick Action Node — sửa nhanh MỘT piece content.

Trước đây việc này được gọi thẳng trong route với một prompt cô lập:

    "Bạn là copywriter. Viết lại bài sau: {body}"

Ba vấn đề, đều thật:

1. `change_hook` ghi kết quả vào `piece.body` và không bao giờ đụng tới
   `piece.hook`. UI render hook riêng, nên bấm "Đổi hook" xong hook hiện ra
   vẫn là hook cũ.

2. Prompt không có brand context, product facts, policies, forbidden_claims,
   mandatory_terms, voice profile hay master message — trong khi generator và
   reviewer chính đều có. Tức là đường sửa nhanh đi vòng qua mọi guardrail,
   rồi kết quả của nó lại được reviewer coi là nội dung đã duyệt.

3. Lượt gọi không vào trace, nên báo cáo chi phí của campaign nói $0.08 trong
   khi user quick-edit mười lần.

Node này nhận đúng context mà channel_renderer nhận, trả structured output có
cả hook lẫn body, và ghi usage vào trace.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from src.knowledge.untrusted import UNTRUSTED_DATA_NOTICE
from src.models.content import ContentPiece
from src.models.trace import NodeTrace
from src.config.settings import get_api_key, get_model_config
from src.utils.callbacks import TokenUsageHandler, estimate_tokens
from src.utils.trace import update_trace

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "v1" / "quick_action.md"

# Mô tả từng việc. Tách khỏi prompt hệ thống để thêm việc mới không phải sửa
# prompt, và để UI với backend dùng chung một danh sách.
ACTIONS = {
    "rewrite": "Viết lại toàn bài, giữ nguyên ý chính nhưng đổi cách diễn đạt.",
    "change_hook": (
        "CHỈ viết lại câu mở đầu (hook). Giữ nguyên phần thân bài và CTA — "
        "trả lại chúng y như cũ."
    ),
    "change_tone": "Viết lại với tone gần gũi, tự nhiên hơn, như đang nói chuyện với bạn bè.",
    "shorter": "Rút xuống còn khoảng 60-70% độ dài hiện tại, giữ ý chính và CTA.",
    "longer": "Mở rộng thêm khoảng 30-40%, thêm chi tiết cụ thể chứ không thêm chữ sáo rỗng.",
}


class QuickActionOutput(BaseModel):
    """Kết quả sửa nhanh. Hook và body tách bạch, không nhập nhèm như trước."""

    hook: Optional[str] = Field(
        default=None,
        description="Câu mở đầu. Để rỗng nếu bài này vốn không tách hook riêng.",
    )
    body: str = Field(description="Toàn bộ thân bài sau khi sửa")
    cta_text: str = Field(default="", description="CTA, giữ nguyên nếu không được yêu cầu đổi")


def _load_prompt() -> str:
    # Knowledge đi thẳng vào prompt này — xem src/knowledge/untrusted.py
    return PROMPT_PATH.read_text(encoding="utf-8") + UNTRUSTED_DATA_NOTICE


def _build_context(state: dict, piece: ContentPiece, action: str) -> str:
    """
    Đúng những gì channel_renderer nhận, cộng thêm bài hiện tại.

    Đây là điểm chính của node: sửa nhanh không được là cửa sau đi vòng qua
    ràng buộc của brand.
    """
    context_pack = state.get("context_pack") or {}
    brief = state.get("brief")
    master_message = state.get("master_message")

    parts = [f"## Việc cần làm\n{ACTIONS.get(action, ACTIONS['rewrite'])}"]

    parts.append(
        "## Bài hiện tại\n"
        f"Kênh: {piece.channel.value} / {piece.deliverable.value}\n"
        f"Hook: {piece.hook or '(bài này không tách hook riêng)'}\n"
        f"Body:\n{piece.body}\n"
        f"CTA: {piece.cta_text}"
    )

    if brief is not None:
        rang_buoc = []
        if brief.brand.forbidden_claims:
            rang_buoc.append("TUYỆT ĐỐI KHÔNG được nói: " + "; ".join(brief.brand.forbidden_claims))
        if brief.brand.mandatory_terms:
            rang_buoc.append("BẮT BUỘC phải có: " + "; ".join(brief.brand.mandatory_terms))
        if brief.constraints.must_avoid:
            rang_buoc.append("Tránh: " + "; ".join(brief.constraints.must_avoid))
        if brief.constraints.must_include:
            rang_buoc.append("Phải nhắc tới: " + "; ".join(brief.constraints.must_include))
        if rang_buoc:
            parts.append("## Ràng buộc bắt buộc\n" + "\n".join(f"- {r}" for r in rang_buoc))

    if master_message is not None:
        parts.append(
            f"## Thông điệp cốt lõi của campaign\n```json\n"
            f"{master_message.model_dump_json(indent=2)}\n```"
        )

    voice = context_pack.get("voice_profile")
    if voice:
        parts.append(
            f"## Giọng brand\n```json\n{json.dumps(voice, ensure_ascii=False, indent=2)}\n```"
        )

    for nhan, khoa in (("Sản phẩm", "product"), ("Quy định nội dung", "policies")):
        if context_pack.get(khoa):
            parts.append(f"## {nhan}\n{context_pack[khoa]}")

    rules = (context_pack.get("platform_rules") or {}).get(piece.channel.value)
    if rules:
        parts.append(f"## Quy tắc nền tảng\n{rules}")

    return "\n\n---\n\n".join(parts)


def quick_action_node(state: dict, piece_index: int, action: str) -> dict:
    """
    Sửa một piece tại chỗ.

    Returns:
        state đã cập nhật. Review cũ bị xoá vì nội dung đã đổi — điểm chấm cho
        bản trước không còn nói gì về bản này.
    """
    pieces = state["campaign_content"].pieces
    piece = pieces[piece_index]

    node_trace = NodeTrace(
        node_name=f"quick_action:{action}",
        started_at=datetime.now(),
        input_summary=f"{piece.channel.value}/{piece.deliverable.value} #{piece_index}",
    )

    config = get_model_config("quick_action") or get_model_config("channel_renderer")
    if not config:
        raise ValueError("Thiếu cấu hình model cho quick_action")

    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatAnthropic(
        model=config["model"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
        api_key=get_api_key(),
    )
    structured = llm.with_structured_output(QuickActionOutput)

    system_prompt = _load_prompt()
    user_message = _build_context(state, piece, action)

    handler = TokenUsageHandler()
    ket_qua = structured.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_message)],
        config={"callbacks": [handler]},
    )

    piece.body = ket_qua.body.strip()
    piece.word_count = len(piece.body.split())
    if ket_qua.cta_text.strip():
        piece.cta_text = ket_qua.cta_text.strip()

    # Đây là chỗ bug cũ: "Đổi hook" ghi vào body và bỏ quên piece.hook, nên UI
    # vẫn hiện hook cũ.
    hook_moi = (ket_qua.hook or "").strip()
    piece.hook = hook_moi or None

    # Hook trùng dòng đầu body thì bỏ, giữ đúng quy ước của channel_renderer
    from src.nodes.channel_renderer import _dedup_content_fields

    pieces[piece_index] = _dedup_content_fields(piece)

    node_trace.model_used = config["model"]
    if handler.has_data:
        node_trace.token_usage = handler.get_usage()
    else:
        node_trace.token_usage = {
            "input": estimate_tokens(system_prompt + user_message),
            "output": estimate_tokens(ket_qua.model_dump_json()),
        }
    node_trace.output_summary = f"{piece.word_count} từ"
    node_trace.finished_at = datetime.now()

    logger.info(
        "Quick action %s trên piece %d: %d vào / %d ra",
        action, piece_index,
        node_trace.token_usage.get("input", 0), node_trace.token_usage.get("output", 0),
    )

    return {
        "campaign_content": state["campaign_content"],
        "trace": update_trace(state, node_trace),
        # Nội dung đã đổi thì điểm chấm cũ không còn nói gì về bản này nữa.
        **invalidate_review(),
    }


def invalidate_review() -> dict:
    """
    Xoá kết quả chấm khi nội dung bị sửa.

    Giữ lại điểm cũ sau khi sửa là để người dùng bàn giao dựa trên một lần chấm
    cho bản khác.
    """
    return {"review_result": None, "review_route": None}
