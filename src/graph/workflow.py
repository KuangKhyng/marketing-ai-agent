"""
Workflow Definition — build the LangGraph StateGraph.

Pipeline flow:
    brief_parser → context_builder → strategist → [HUMAN APPROVE]
                                                         │
                                                    (approved?)
                                                    /         \\
                                                  Yes          No → END
                                                   │
                                           message_architect
                                                   │
                                           channel_renderer
                                                   │
                                              reviewer
                                                   │
                                             (passed?)
                                            /         \\
                                          Yes          No → (revision_count < max?)
                                           │                    /          \\
                                      formatter              Yes           No → formatter
                                           │                   │
                                         END          message_architect (with feedback)
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from src.graph.state import CampaignState
from src.graph.edges import route_after_review, route_after_approval
from src.nodes.brief_parser import brief_parser_node
from src.nodes.context_builder import context_builder_node
from src.nodes.strategist import strategist_node
from src.nodes.message_architect import message_architect_node
from src.nodes.channel_renderer import channel_renderer_node
from src.nodes.reviewer import reviewer_node
from src.nodes.formatter import formatter_node


def human_approval_node(state: dict) -> dict:
    """
    Human approval gate — separate node that uses interrupt() to pause.

    Displays the strategy to the user and waits for approval.
    The CLI handles the actual user interaction and resumes the workflow.
    """
    strategy = state.get("strategy", "No strategy generated.")

    # interrupt() pauses the workflow here
    # The value passed to interrupt() is what the CLI will display
    user_response = interrupt({
        "type": "approval_request",
        "strategy": strategy,
        "message": "Please review the campaign strategy above.",
    })

    # When resumed, user_response contains the user's decision
    if isinstance(user_response, dict):
        approved = user_response.get("approved", False)
    elif isinstance(user_response, str):
        approved = user_response.lower() in ("approve", "a", "yes", "y")
    else:
        approved = bool(user_response)

    return {
        "human_approved": approved,
        "current_node": "human_approval",
    }


def build_workflow():
    """
    Build and compile the LangGraph workflow.

    Returns:
        CompiledGraph with MemorySaver checkpointer.
    """
    graph = StateGraph(CampaignState)

    # Add nodes
    graph.add_node("brief_parser", brief_parser_node)
    graph.add_node("context_builder", context_builder_node)
    graph.add_node("strategist", strategist_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("message_architect", message_architect_node)
    graph.add_node("channel_renderer", channel_renderer_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("formatter", formatter_node)

    # Set entry point
    graph.set_entry_point("brief_parser")

    # Linear edges
    graph.add_edge("brief_parser", "context_builder")
    graph.add_edge("context_builder", "strategist")
    graph.add_edge("strategist", "human_approval")

    # Conditional: human approved?
    graph.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {"continue": "message_architect", "end": END},
    )

    # Linear edges
    graph.add_edge("message_architect", "channel_renderer")
    graph.add_edge("channel_renderer", "reviewer")

    # Conditional: review passed?
    graph.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "passed": "formatter",
            "retry": "message_architect",
            "max_retries": "formatter",  # output anyway with warnings
        },
    )

    graph.add_edge("formatter", END)

    # Compile with memory checkpointer (required for interrupt)
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)
