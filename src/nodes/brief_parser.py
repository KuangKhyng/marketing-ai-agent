"""
Brief Parser Node
- Input: raw_input (natural language)
- Output: CampaignBrief (Pydantic model)
- Model: Claude Haiku (fast, cheap — parsing task)
- Type: Deterministic

Uses Claude API with tool_use / structured output to force correct CampaignBrief schema.
"""
import logging
from datetime import datetime
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.brief import CampaignBrief
from src.models.trace import NodeTrace
from src.config.settings import get_api_key, get_model_config
from src.utils.trace import update_trace
from src.utils.callbacks import TokenUsageHandler, estimate_tokens
from src.knowledge.brand_manager import BrandManager


logger = logging.getLogger(__name__)

# Load prompt template
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "v1" / "brief_parser.md"


def _load_prompt() -> str:
    """Load the brief parser prompt template."""
    return PROMPT_PATH.read_text(encoding="utf-8")


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
            "trace": update_trace(state, node_trace),
        }

    try:
        brief = _call_claude_for_brief(state["raw_input"], config, node_trace)

        # ARCHITECTURAL FIX: Brand comes from UI, not from LLM
        brief = _override_brand_from_state(brief, state)
        
        node_trace.output_summary = f"Parsed brief: goal={brief.goal.value}, channels={[c.value for c in brief.channels]}"
        node_trace.finished_at = datetime.now()

        return {
            "brief": brief,
            "current_node": "brief_parser",
            "trace": update_trace(state, node_trace),
        }

    except Exception as e:
        # Retry once with more explicit instructions
        try:
            brief = _call_claude_for_brief(
                state["raw_input"], config, node_trace,
                retry_hint="Lần trước bạn trả về sai format. Hãy trả về CHÍNH XÁC theo schema CampaignBrief. Mọi field enum phải dùng đúng giá trị cho phép."
            )
            
            # ARCHITECTURAL FIX: Brand comes from UI, not from LLM
            brief = _override_brand_from_state(brief, state)
            
            node_trace.output_summary = f"Parsed brief (retry): goal={brief.goal.value}"
            node_trace.finished_at = datetime.now()

            return {
                "brief": brief,
                "current_node": "brief_parser",
                "trace": update_trace(state, node_trace),
            }
        except Exception as retry_error:
            node_trace.error = f"Brief parsing failed after retry: {str(retry_error)}"
            node_trace.finished_at = datetime.now()
            return {
                "error": node_trace.error,
                "current_node": "brief_parser",
                "trace": update_trace(state, node_trace),
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

    handler = TokenUsageHandler()
    result = structured_llm.invoke(messages, config={"callbacks": [handler]})

    # Track token usage
    node_trace.model_used = config["model"]
    if handler.has_data:
        node_trace.token_usage = handler.get_usage()
    else:
        # Fallback: estimate from content length
        input_text = system_prompt + raw_input
        output_text = result.model_dump_json()
        node_trace.token_usage = {
            "input": estimate_tokens(input_text),
            "output": estimate_tokens(output_text),
        }

    return result


def _clear_brand(brief: CampaignBrief, name: str = "", voice_profile_id: str = "default") -> None:
    """
    Bỏ mọi thông tin brand mà LLM trả về.

    Quan trọng nhất là forbidden_claims và mandatory_terms: reviewer dùng chúng
    làm QUY TẮC CỨNG (_run_rule_checks), chiều nào vi phạm là trượt bất kể điểm.
    Một mandatory_terms do LLM bịa sẽ làm MỌI bài trượt vì thiếu một từ chẳng ai
    yêu cầu; một forbidden_claims bịa sẽ cấm điều chẳng ai cấm.

    Nên: không xác nhận được từ kho brand thì phải xoá, không được để lại.
    """
    brief.brand.name = name
    brief.brand.voice_profile_id = voice_profile_id
    brief.brand.forbidden_claims = []
    brief.brand.mandatory_terms = []


def _override_brand_from_state(brief: CampaignBrief, state: dict) -> CampaignBrief:
    """
    Override brand fields based on what user selected in UI.
    
    ARCHITECTURAL PRINCIPLE: Brief Parser NEVER determines brand.
    Brand comes from UI selection (state["brand_id"]), not from LLM.
    This function guarantees brand info is always correct regardless
    of what LLM hallucinated.
    """
    brand_id = state.get("brand_id")

    if brand_id:
        # User selected a brand in UI → load brand metadata
        try:
            manager = BrandManager()
            brand_data = manager.get_brand(brand_id)

            if brand_data:
                brief.brand.name = brand_data.get("name", brand_id)
                brief.brand.voice_profile_id = brand_id
                brief.brand.forbidden_claims = brand_data.get("forbidden_claims", [])
                brief.brand.mandatory_terms = brand_data.get("mandatory_terms", [])
            else:
                # Brand không tra được — coi như generic
                _clear_brand(brief, voice_profile_id="default")
        except Exception:
            logger.warning(
                "Không đọc được kho brand cho '%s' — bỏ mọi thông tin brand do LLM trả về",
                brand_id,
            )
            _clear_brand(brief, name=brand_id, voice_profile_id=brand_id)
    else:
        # Generic mode — FORCE empty brand, override anything LLM bịa
        _clear_brand(brief, voice_profile_id="default")

    return brief
