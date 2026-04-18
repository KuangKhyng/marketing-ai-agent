"""
Strategist Node
- Input: CampaignBrief + context_pack
- Output: strategy (string — campaign strategy)
- Model: Claude Sonnet (needs reasoning + creativity)
- Type: Agentic

Note: After this node, there is a HUMAN APPROVAL gate.
"""
from datetime import datetime
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.trace import NodeTrace
from src.config.settings import get_api_key, get_model_config
from src.utils.trace import update_trace
from src.utils.callbacks import TokenUsageHandler, estimate_tokens

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "v1" / "strategist.md"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def strategist_node(state: dict) -> dict:
    """
    Generate campaign strategy from brief and context.

    Args:
        state: CampaignState dict with 'brief' and 'context_pack' keys.

    Returns:
        Updated state with 'strategy' key.
    """
    # Early exit if previous node errored
    if state.get("error"):
        return {"current_node": "strategist"}

    node_trace = NodeTrace(
        node_name="strategist",
        started_at=datetime.now(),
        input_summary=f"Strategy for: {state['brief'].offer.product_or_service}, goal={state['brief'].goal.value}",
    )

    config = get_model_config("strategist")

    try:
        llm = ChatAnthropic(
            model=config["model"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            api_key=get_api_key(),
        )

        system_prompt = _load_prompt()

        # Build the context message
        brief = state["brief"]
        context_pack = state["context_pack"]

        user_message = _build_user_message(brief, context_pack, state.get("strategy_feedback"))

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        handler = TokenUsageHandler()
        response = llm.invoke(messages, config={"callbacks": [handler]})
        strategy = response.content

        node_trace.model_used = config["model"]
        node_trace.output_summary = strategy[:200] + "..." if len(strategy) > 200 else strategy

        # Token usage
        if handler.has_data:
            node_trace.token_usage = handler.get_usage()
        else:
            # Try from response metadata
            usage = _extract_token_usage(response)
            if usage:
                node_trace.token_usage = usage
            else:
                node_trace.token_usage = {
                    "input": estimate_tokens(system_prompt + user_message),
                    "output": estimate_tokens(strategy),
                }

        node_trace.finished_at = datetime.now()

        return {
            "strategy": strategy,
            "current_node": "strategist",
            "trace": update_trace(state, node_trace),
        }

    except Exception as e:
        node_trace.error = f"Strategy generation failed: {str(e)}"
        node_trace.finished_at = datetime.now()
        return {
            "error": node_trace.error,
            "current_node": "strategist",
            "trace": update_trace(state, node_trace),
        }


def _build_user_message(brief, context_pack: dict, strategy_feedback: str = None) -> str:
    """Build the detailed user message with brief and context."""
    brief_json = brief.model_dump_json(indent=2)

    sections = [
        f"## Campaign Brief\n```json\n{brief_json}\n```",
        f"## Brand Context\n{context_pack.get('brand', 'N/A')}",
        f"## Product/Service Info\n{context_pack.get('product', 'N/A')}",
        f"## Audience Persona\n{context_pack.get('audience', 'N/A')}",
        f"## Content Policies\n{context_pack.get('policies', 'N/A')}",
    ]

    # Add platform rules
    platform_rules = context_pack.get("platform_rules", {})
    if platform_rules:
        rules_text = "\n\n".join(
            f"### {platform}\n{rules}" for platform, rules in platform_rules.items()
        )
        sections.append(f"## Platform Rules\n{rules_text}")

    # Add additional context if present
    if context_pack.get("additional_context"):
        sections.append(f"## Additional Context (HIGHEST PRIORITY)\n{context_pack['additional_context']}")

    # Inject user feedback if this is a strategy revision
    if strategy_feedback:
        sections.append(
            f"## ⚠️ USER FEEDBACK — BẮT BUỘC PHẢI SỬA\n"
            f"User đã review strategy trước đó và yêu cầu sửa:\n\n"
            f"{strategy_feedback}\n\n"
            f"Hãy viết lại strategy MỚI HOÀN TOÀN, address tất cả feedback trên."
        )

    return "\n\n---\n\n".join(sections)


def _extract_token_usage(response) -> dict[str, int] | None:
    """Extract token usage from LangChain response if available."""
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        return {
            "input": response.usage_metadata.get("input_tokens", 0),
            "output": response.usage_metadata.get("output_tokens", 0),
        }
    if hasattr(response, "response_metadata"):
        meta = response.response_metadata
        if "usage" in meta:
            return {
                "input": meta["usage"].get("input_tokens", 0),
                "output": meta["usage"].get("output_tokens", 0),
            }
    return None
