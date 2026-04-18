"""
Context Builder Node
- Input: CampaignBrief
- Output: context_pack (dict)
- Model: None (Phase 1) — pure file loading + filtering
- Type: Deterministic

Assembles context from knowledge base following priority hierarchy.
"""
from datetime import datetime

from src.models.trace import NodeTrace, RunTrace
from src.knowledge.retriever import build_context_pack
from src.config.settings import estimate_cost


def context_builder_node(state: dict) -> dict:
    """
    Assemble context pack from knowledge base based on the brief.

    Args:
        state: CampaignState dict with 'brief' key.

    Returns:
        Updated state with 'context_pack' key.
    """
    node_trace = NodeTrace(
        node_name="context_builder",
        started_at=datetime.now(),
        input_summary=f"Building context for: {state['brief'].offer.product_or_service}",
    )

    try:
        brief = state["brief"]
        context_pack = build_context_pack(brief)

        # Summarize what was loaded
        loaded_keys = [k for k, v in context_pack.items() if v]
        node_trace.output_summary = f"Loaded context: {', '.join(loaded_keys)}"
        node_trace.retrieved_context_ids = loaded_keys
        node_trace.finished_at = datetime.now()

        return {
            "context_pack": context_pack,
            "current_node": "context_builder",
            "trace": _update_trace(state, node_trace),
        }

    except Exception as e:
        node_trace.error = f"Context building failed: {str(e)}"
        node_trace.finished_at = datetime.now()
        return {
            "error": node_trace.error,
            "current_node": "context_builder",
            "trace": _update_trace(state, node_trace),
        }


def _update_trace(state: dict, node_trace: NodeTrace):
    """Update the run trace with a new node trace."""
    trace = state.get("trace") or RunTrace()
    trace.node_traces.append(node_trace)
    return trace
