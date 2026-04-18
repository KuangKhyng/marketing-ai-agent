"""
Context Builder Node
- Input: CampaignBrief
- Output: context_pack (dict)
- Model: None (Phase 1) — pure file loading + filtering
- Type: Deterministic

Assembles context from knowledge base following priority hierarchy.
"""
from datetime import datetime

from src.models.trace import NodeTrace
from src.knowledge.retriever import build_context_pack
from src.utils.trace import update_trace


def context_builder_node(state: dict) -> dict:
    """
    Assemble context pack from knowledge base based on the brief.

    Args:
        state: CampaignState dict with 'brief' key.

    Returns:
        Updated state with 'context_pack' key.
    """
    # Early exit if previous node errored
    if state.get("error"):
        return {"current_node": "context_builder"}

    node_trace = NodeTrace(
        node_name="context_builder",
        started_at=datetime.now(),
        input_summary=f"Building context for: {state['brief'].offer.product_or_service}",
    )

    try:
        brief = state["brief"]
        brand_id = state.get("brand_id")  # None = generic mode

        context_pack = build_context_pack(brief, brand_id=brand_id)

        # Summarize what was loaded
        loaded_keys = [k for k, v in context_pack.items() if v]
        mode = context_pack.get("mode", "generic")
        node_trace.output_summary = f"Mode: {mode}, brand: {brand_id or 'generic'}, loaded: {', '.join(loaded_keys)}"
        node_trace.retrieved_context_ids = loaded_keys
        node_trace.finished_at = datetime.now()

        return {
            "context_pack": context_pack,
            "current_node": "context_builder",
            "trace": update_trace(state, node_trace),
        }

    except Exception as e:
        node_trace.error = f"Context building failed: {str(e)}"
        node_trace.finished_at = datetime.now()
        return {
            "error": node_trace.error,
            "current_node": "context_builder",
            "trace": update_trace(state, node_trace),
        }
