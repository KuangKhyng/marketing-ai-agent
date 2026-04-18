"""
Campaign State — shared state for the LangGraph workflow.

CampaignState is a TypedDict that flows through all nodes.
Each node reads what it needs and updates relevant keys.
"""
from typing import TypedDict, Optional, Annotated
from src.models.brief import CampaignBrief
from src.models.message import MasterMessage
from src.models.content import CampaignContent
from src.models.review import ReviewResult
from src.models.trace import RunTrace


class CampaignState(TypedDict):
    # Input
    raw_input: str                              # user's natural language input

    # Parsed
    brief: Optional[CampaignBrief]              # structured brief from Brief Parser

    # Context
    context_pack: Optional[dict]                # assembled context from knowledge base
                                                 # {"brand": str, "product": str, "audience": str,
                                                 #  "platform_rules": dict[str, str], "policies": str}

    # Strategy
    strategy: Optional[str]                     # campaign strategy from Strategist (text)
    human_approved: bool                        # whether human approved the strategy

    # Content
    master_message: Optional[MasterMessage]     # platform-agnostic message architecture
    campaign_content: Optional[CampaignContent] # rendered content per platform

    # Review
    review_result: Optional[ReviewResult]       # review scores and feedback
    revision_count: int                         # number of revision loops done
    max_revisions: int                          # max allowed (default 2)

    # Trace
    trace: Optional[RunTrace]                   # full run trace

    # Control
    current_node: str                           # which node is currently active
    error: Optional[str]                        # error message if any
