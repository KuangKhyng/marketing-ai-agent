from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Optional
import uuid


class NodeTrace(BaseModel):
    node_name: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    model_used: Optional[str] = None
    input_summary: str = ""
    output_summary: str = ""
    retrieved_context_ids: list[str] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=dict)  # {"input": N, "output": M}
    error: Optional[str] = None


class RunTrace(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    brief_summary: str = ""
    node_traces: list[NodeTrace] = Field(default_factory=list)
    total_cost_estimate: float = 0.0
    revision_count: int = 0
    final_status: str = "running"  # running, completed, failed, human_rejected
