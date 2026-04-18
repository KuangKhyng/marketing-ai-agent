"""
Message Architect Node
- Input: CampaignBrief + context_pack + strategy (approved)
- Output: MasterMessage (Pydantic model)
- Model: Claude Sonnet (needs creativity + structured output)
- Type: Agentic

MasterMessage is PLATFORM-AGNOSTIC — the "skeleton" that Channel Renderer uses.
Handles revision_instructions from reviewer if in revision loop.
"""
import json
from datetime import datetime
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.message import MasterMessage
from src.models.trace import NodeTrace, RunTrace
from src.config.settings import get_api_key, get_model_config, estimate_cost

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "v1" / "message_architect.md"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def message_architect_node(state: dict) -> dict:
    """
    Generate platform-agnostic MasterMessage from strategy and context.

    Args:
        state: CampaignState dict with 'brief', 'context_pack', 'strategy' keys.
            May also have 'review_result' with revision_instructions on retry.

    Returns:
        Updated state with 'master_message' key.
    """
    node_trace = NodeTrace(
        node_name="message_architect",
        started_at=datetime.now(),
        input_summary=f"Creating master message for: {state['brief'].offer.product_or_service}",
    )

    config = get_model_config("message_architect")

    try:
        master_message = _call_claude_for_message(state, config, node_trace)

        node_trace.output_summary = f"Core promise: {master_message.core_promise}"
        node_trace.finished_at = datetime.now()

        return {
            "master_message": master_message,
            "current_node": "message_architect",
            "trace": _update_trace(state, node_trace),
        }

    except Exception as e:
        # Retry once
        try:
            master_message = _call_claude_for_message(
                state, config, node_trace,
                retry_hint="Lần trước bạn trả về sai format. Hãy trả về CHÍNH XÁC theo schema MasterMessage JSON."
            )
            node_trace.output_summary = f"Core promise (retry): {master_message.core_promise}"
            node_trace.finished_at = datetime.now()

            return {
                "master_message": master_message,
                "current_node": "message_architect",
                "trace": _update_trace(state, node_trace),
            }
        except Exception as retry_error:
            node_trace.error = f"Message architecture failed after retry: {str(retry_error)}"
            node_trace.finished_at = datetime.now()
            return {
                "error": node_trace.error,
                "current_node": "message_architect",
                "trace": _update_trace(state, node_trace),
            }


def _call_claude_for_message(
    state: dict,
    config: dict,
    node_trace: NodeTrace,
    retry_hint: str = "",
) -> MasterMessage:
    """Call Claude API with structured output to get MasterMessage."""
    llm = ChatAnthropic(
        model=config["model"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
        api_key=get_api_key(),
    )

    system_prompt = _load_prompt()
    if retry_hint:
        system_prompt += f"\n\n## RETRY NOTE\n{retry_hint}"

    structured_llm = llm.with_structured_output(MasterMessage)

    # Build user message
    brief = state["brief"]
    context_pack = state["context_pack"]
    strategy = state["strategy"]

    user_parts = [
        f"## Campaign Brief\n```json\n{brief.model_dump_json(indent=2)}\n```",
        f"## Approved Strategy\n{strategy}",
        f"## Brand Context\n{context_pack.get('brand', 'N/A')}",
        f"## Product Info\n{context_pack.get('product', 'N/A')}",
        f"## Content Policies\n{context_pack.get('policies', 'N/A')}",
    ]

    # Add revision instructions if this is a retry after review
    review_result = state.get("review_result")
    if review_result and review_result.revision_instructions:
        user_parts.append(
            f"## ⚠️ REVISION REQUIRED\n"
            f"Content trước đã bị reject bởi reviewer. Hãy sửa theo hướng dẫn sau:\n\n"
            f"{review_result.revision_instructions}\n\n"
            f"### Critical Issues:\n" +
            "\n".join(f"- {issue}" for issue in review_result.critical_issues)
        )

    user_message = "\n\n---\n\n".join(user_parts)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    result = structured_llm.invoke(messages)

    node_trace.model_used = config["model"]
    node_trace.token_usage = {"input": 0, "output": 0}

    return result


def _update_trace(state: dict, node_trace: NodeTrace):
    trace = state.get("trace") or RunTrace()
    trace.node_traces.append(node_trace)
    if node_trace.model_used and node_trace.token_usage:
        cost = estimate_cost(
            node_trace.model_used,
            node_trace.token_usage.get("input", 0),
            node_trace.token_usage.get("output", 0),
        )
        trace.total_cost_estimate += cost
    return trace
