"""Shared trace utilities — used by all nodes."""
from src.models.trace import NodeTrace, RunTrace
from src.config.settings import estimate_cost


def update_trace(state: dict, node_trace: NodeTrace) -> RunTrace:
    """
    Update the run trace with a new node trace.

    Args:
        state: current CampaignState dict
        node_trace: the NodeTrace to append

    Returns:
        Updated RunTrace
    """
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
