"""
Brief Parser Node
- Input: raw_input (natural language)
- Output: CampaignBrief (Pydantic model)
- Model: Claude Haiku (fast, cheap — parsing task)
- Type: Deterministic

Uses Claude API with tool_use / structured output to force correct CampaignBrief schema.
"""
import json
from datetime import datetime
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.brief import CampaignBrief
from src.models.trace import NodeTrace
from src.config.settings import get_api_key, get_model_config, estimate_cost


# Load prompt template
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "v1" / "brief_parser.md"


def _load_prompt() -> str:
    """Load the brief parser prompt template."""
    return PROMPT_PATH.read_text(encoding="utf-8")


def _get_brief_tool_schema() -> dict:
    """Generate the tool schema from CampaignBrief Pydantic model."""
    return {
        "name": "create_campaign_brief",
        "description": "Create a structured campaign brief from natural language input. Extract all information and fill in reasonable defaults for missing fields.",
        "input_schema": CampaignBrief.model_json_schema(),
    }


def brief_parser_node(state: dict) -> dict:
    """
    Parse natural language input into a structured CampaignBrief.

    Args:
        state: CampaignState dict with 'raw_input' key.

    Returns:
        Updated state with 'brief' and 'trace' keys.
    """
    node_trace = NodeTrace(
        node_name="brief_parser",
        started_at=datetime.now(),
        input_summary=state["raw_input"][:200],
    )

    config = get_model_config("brief_parser")
    if not config:
        node_trace.error = "No model config for brief_parser"
        node_trace.finished_at = datetime.now()
        return {
            "error": node_trace.error,
            "current_node": "brief_parser",
            "trace": _update_trace(state, node_trace),
        }

    try:
        brief = _call_claude_for_brief(state["raw_input"], config, node_trace)
        node_trace.output_summary = f"Parsed brief: goal={brief.goal.value}, channels={[c.value for c in brief.channels]}"
        node_trace.finished_at = datetime.now()

        return {
            "brief": brief,
            "current_node": "brief_parser",
            "trace": _update_trace(state, node_trace),
        }

    except Exception as e:
        # Retry once with more explicit instructions
        try:
            brief = _call_claude_for_brief(
                state["raw_input"], config, node_trace,
                retry_hint="Lần trước bạn trả về sai format. Hãy trả về CHÍNH XÁC theo schema CampaignBrief. Mọi field enum phải dùng đúng giá trị cho phép."
            )
            node_trace.output_summary = f"Parsed brief (retry): goal={brief.goal.value}"
            node_trace.finished_at = datetime.now()

            return {
                "brief": brief,
                "current_node": "brief_parser",
                "trace": _update_trace(state, node_trace),
            }
        except Exception as retry_error:
            node_trace.error = f"Brief parsing failed after retry: {str(retry_error)}"
            node_trace.finished_at = datetime.now()
            return {
                "error": node_trace.error,
                "current_node": "brief_parser",
                "trace": _update_trace(state, node_trace),
            }


def _call_claude_for_brief(
    raw_input: str,
    config: dict,
    node_trace: NodeTrace,
    retry_hint: str = "",
) -> CampaignBrief:
    """Call Claude API with tool_use to get structured CampaignBrief."""
    llm = ChatAnthropic(
        model=config["model"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
        api_key=get_api_key(),
    )

    system_prompt = _load_prompt()
    if retry_hint:
        system_prompt += f"\n\n## RETRY NOTE\n{retry_hint}"

    # Use with_structured_output for Pydantic model
    structured_llm = llm.with_structured_output(CampaignBrief)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Phân tích input sau thành CampaignBrief:\n\n{raw_input}"),
    ]

    result = structured_llm.invoke(messages)

    # Track token usage (approximate — structured output doesn't always expose usage)
    node_trace.model_used = config["model"]
    node_trace.token_usage = {"input": 0, "output": 0}  # Will be filled by callback if available

    return result


def _update_trace(state: dict, node_trace: NodeTrace):
    """Update the run trace with a new node trace."""
    from src.models.trace import RunTrace
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
