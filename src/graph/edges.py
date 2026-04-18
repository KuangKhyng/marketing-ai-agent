"""
Conditional Edge Functions — routing logic for the LangGraph workflow.
"""


def route_after_review(state: dict) -> str:
    """
    Route after the reviewer node.

    Returns:
        - "passed": content passed review → go to formatter
        - "retry": content failed but retries available → go to message_architect
        - "max_retries": content failed and no retries left → go to formatter (with warnings)
    """
    review_result = state.get("review_result")

    # If no review result (error), pass through
    if review_result is None:
        return "passed"

    if review_result.overall_passed:
        return "passed"

    # Check revision count
    revision_count = state.get("revision_count", 0)
    max_revisions = state.get("max_revisions", 2)

    if revision_count < max_revisions:
        return "retry"
    else:
        return "max_retries"


def route_after_approval(state: dict) -> str:
    """
    Route after the human approval node.

    Returns:
        - "continue": human approved → go to message_architect
        - "end": human rejected → end workflow
    """
    if state.get("human_approved", False):
        return "continue"
    return "end"
