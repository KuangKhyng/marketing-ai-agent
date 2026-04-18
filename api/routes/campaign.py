from fastapi import APIRouter, HTTPException
import uuid

from api.schemas import (
    CampaignInput, BriefEdit, StrategyFeedback,
    ContentFeedback, PipelineStatus,
)
from api.pipeline_runner import PipelineRunner

router = APIRouter()

from datetime import datetime, timedelta
from threading import Lock

# Session với TTL để tránh memory leak
class SessionStore:
    def __init__(self, ttl_minutes: int = 60):
        self._sessions: dict[str, dict] = {}
        self._lock = Lock()
        self.ttl = timedelta(minutes=ttl_minutes)

    def set(self, run_id: str, runner: PipelineRunner):
        with self._lock:
            self._sessions[run_id] = {
                "runner": runner,
                "created_at": datetime.now(),
            }
            self._cleanup()

    def get(self, run_id: str) -> PipelineRunner | None:
        with self._lock:
            entry = self._sessions.get(run_id)
            if not entry:
                return None
            if datetime.now() - entry["created_at"] > self.ttl:
                del self._sessions[run_id]
                return None
            return entry["runner"]
            
    def __setitem__(self, run_id: str, runner):
        self.set(run_id, runner)

    def _cleanup(self):
        now = datetime.now()
        expired = [k for k, v in self._sessions.items() if now - v["created_at"] > self.ttl]
        for k in expired:
            del self._sessions[k]

    @property
    def count(self) -> int:
        return len(self._sessions)

sessions = SessionStore(ttl_minutes=120)


@router.post("/start", response_model=PipelineStatus)
def start_campaign(input: CampaignInput):
    """
    Start a new campaign pipeline.
    Runs Phase 1 (parse brief + build context).
    Returns brief for review.
    """
    if input.brand_id:
        from src.knowledge.brand_manager import BrandManager
        manager = BrandManager()
        if not manager.get_brand(input.brand_id):
            raise HTTPException(status_code=404, detail=f"Brand '{input.brand_id}' not found")

    runner = PipelineRunner()
    raw_input = input.to_raw_input()

    state = runner.phase_1_parse(raw_input, brand_id=input.brand_id)

    if state.get("error"):
        raise HTTPException(status_code=500, detail=state["error"])

    run_id = state["trace"].run_id
    sessions[run_id] = runner

    context_pack = state.get("context_pack", {})
    from api.schemas import ContextInfo
    context_info = ContextInfo(
        mode=context_pack.get("mode", "generic"),
        brand_name=context_pack.get("brand_name", ""),
        loaded_docs=context_pack.get("loaded_docs", []),
        total_tokens_estimate=len(str(context_pack)) // 4
    )

    return PipelineStatus(
        run_id=run_id,
        phase="brief_review",
        brief=state["brief"].model_dump() if state.get("brief") else None,
        cost_estimate=state["trace"].total_cost_estimate,
        context_info=context_info,
    )


@router.post("/{run_id}/approve-brief", response_model=PipelineStatus)
def approve_brief(run_id: str, edit: BriefEdit = None):
    """
    Approve (or edit) the parsed brief, then generate strategy.
    Runs Phase 2 (strategist).
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    # Apply edits if any
    if edit:
        runner.update_brief_fields(edit)

    state = runner.phase_2_strategy()

    if state.get("error"):
        raise HTTPException(status_code=500, detail=state["error"])

    return PipelineStatus(
        run_id=run_id,
        phase="strategy_review",
        brief=state["brief"].model_dump(),
        strategy=state.get("strategy"),
        cost_estimate=state["trace"].total_cost_estimate,
    )


@router.post("/{run_id}/review-strategy", response_model=PipelineStatus)
def review_strategy(run_id: str, feedback: StrategyFeedback):
    """
    Review strategy — approve or request revision.
    If approved, runs Phase 3 (message architect + channel renderer).
    If revision requested, re-runs strategist with feedback.
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    if not feedback.approved:
        # Compile feedback and re-run strategist
        feedback_text = _compile_strategy_feedback(feedback)
        state = runner.phase_2_strategy(feedback=feedback_text)

        return PipelineStatus(
            run_id=run_id,
            phase="strategy_review",  # Stay on strategy review
            strategy=state.get("strategy"),
            cost_estimate=state["trace"].total_cost_estimate,
        )

    # Approved — generate content
    state = runner.phase_3_content()

    if state.get("error"):
        raise HTTPException(status_code=500, detail=state["error"])

    return PipelineStatus(
        run_id=run_id,
        phase="content_review",
        master_message=state["master_message"].model_dump() if state.get("master_message") else None,
        content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
        cost_estimate=state["trace"].total_cost_estimate,
    )


@router.post("/{run_id}/review-content", response_model=PipelineStatus)
def review_content(run_id: str, feedback: ContentFeedback):
    """
    Review content — approve all or request revision on specific pieces.
    If approved, runs Phase 4 (reviewer).
    If revision requested, re-runs content generation with feedback.
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    # Apply inline edits
    for pf in feedback.piece_feedbacks:
        if pf.edited_body:
            runner.update_content_piece(pf.piece_index, pf.edited_body)

    if not feedback.approved:
        feedback_text = _compile_content_feedback(feedback)
        state = runner.phase_3_content(feedback=feedback_text)

        return PipelineStatus(
            run_id=run_id,
            phase="content_review",
            content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
            revision_count=state.get("revision_count", 0),
            cost_estimate=state["trace"].total_cost_estimate,
        )

    # Approved — run automated review
    state = runner.phase_4_review()

    return PipelineStatus(
        run_id=run_id,
        phase="final_review",
        content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
        review_result=state["review_result"].model_dump() if state.get("review_result") else None,
        cost_estimate=state["trace"].total_cost_estimate,
    )


@router.post("/{run_id}/quick-action")
def quick_action(run_id: str, action: dict):
    """
    Quick action on a single content piece.
    Actions: rewrite, change_hook, change_tone, shorter, longer
    """
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    piece_index = action.get("piece_index", 0)
    action_type = action.get("action", "rewrite")
    pieces = runner.state["campaign_content"].pieces

    if piece_index >= len(pieces):
        raise HTTPException(status_code=400, detail="Invalid piece index")

    piece = pieces[piece_index]
    original = piece.body

    action_prompts = {
        "rewrite": f"Viết lại hoàn toàn bài sau, giữ nguyên ý chính nhưng thay đổi cách diễn đạt:\n\n{original}",
        "change_hook": f"Giữ nguyên nội dung chính, chỉ viết lại câu mở đầu (hook) cho hấp dẫn hơn:\n\n{original}",
        "change_tone": f"Viết lại bài sau với tone casual, gần gũi hơn, như đang nói chuyện với bạn bè:\n\n{original}",
        "shorter": f"Rút gọn bài sau xuống còn 60-70% độ dài hiện tại, giữ ý chính:\n\n{original}",
        "longer": f"Mở rộng bài sau thêm 30-40% độ dài, thêm chi tiết và ví dụ:\n\n{original}",
    }

    prompt = action_prompts.get(action_type, action_prompts["rewrite"])

    from src.config.settings import get_api_key, get_model_config
    config = get_model_config('channel_renderer')
    llm = ChatAnthropic(
        model=config.get('model', 'claude-3-5-haiku-20241022'),
        temperature=config.get('temperature', 0.7),
        max_tokens=config.get('max_tokens', 2000),
        api_key=get_api_key(),
    )

    result = llm.invoke([
        SystemMessage(content=f"Bạn là copywriter. Channel: {piece.channel.value}. Deliverable: {piece.deliverable.value}. Chỉ trả về nội dung mới, không giải thích."),
        HumanMessage(content=prompt),
    ])

    new_body = result.content.strip()
    piece.body = new_body
    piece.word_count = len(new_body.split())

    return {
        "piece_index": piece_index,
        "new_body": new_body,
        "word_count": piece.word_count,
        "action": action_type,
    }

@router.post("/{run_id}/approve-final", response_model=PipelineStatus)
def approve_final(run_id: str):
    """
    Final approval — format and save output.
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    state = runner.phase_5_export()

    return PipelineStatus(
        run_id=run_id,
        phase="completed",
        content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
        review_result=state["review_result"].model_dump() if state.get("review_result") else None,
        cost_estimate=state["trace"].total_cost_estimate,
    )


@router.get("/{run_id}/download/{format}")
def download_output(run_id: str, format: str):
    """Download output in specified format (md, json)."""
    from fastapi.responses import FileResponse
    from src.config.settings import PROJECT_ROOT

    run_dir = PROJECT_ROOT / "outputs" / run_id
    if format == "md":
        path = run_dir / "content.md"
    elif format == "json":
        path = run_dir / "content.json"
    else:
        raise HTTPException(status_code=400, detail="Format must be 'md' or 'json'")

    if not path.exists():
        raise HTTPException(status_code=404, detail="Output not found")

    return FileResponse(path, filename=f"campaign-{run_id}.{format}")


@router.get("/history")
def list_campaigns():
    """List past campaign runs from outputs/ directory."""
    from src.config.settings import PROJECT_ROOT
    import json

    outputs_dir = PROJECT_ROOT / "outputs"
    runs = []
    if outputs_dir.exists():
        for run_dir in sorted(outputs_dir.iterdir(), reverse=True):
            if run_dir.is_dir():
                trace_path = run_dir / "trace.json"
                if trace_path.exists():
                    trace = json.loads(trace_path.read_text(encoding="utf-8"))
                    runs.append({
                        "run_id": run_dir.name,
                        "brief_summary": trace.get("brief_summary", ""),
                        "status": trace.get("final_status", "unknown"),
                        "cost": trace.get("total_cost_estimate", 0),
                        "timestamp": trace.get("started_at", ""),
                    })
    return runs


def _compile_strategy_feedback(feedback: StrategyFeedback) -> str:
    parts = []
    check_labels = {
        "tone": "Tone chưa phù hợp — cần điều chỉnh",
        "angle": "Góc tiếp cận chưa đúng",
        "audience": "Chưa hiểu đúng audience",
        "hook": "Hook chưa đủ mạnh",
        "cta": "CTA chưa rõ ràng",
        "platform": "Platform approach chưa đúng",
    }
    for check in feedback.feedback_checks:
        if check in check_labels:
            parts.append(check_labels[check])
    if feedback.comment:
        parts.append(f"User comment: {feedback.comment}")
    return "\n".join(f"- {p}" for p in parts)


def _compile_content_feedback(feedback: ContentFeedback) -> str:
    parts = ["User yêu cầu sửa các piece sau:"]
    for pf in feedback.piece_feedbacks:
        if not pf.approved:
            parts.append(f"- Piece #{pf.piece_index}: {pf.comment or 'Cần sửa'}")
    return "\n".join(parts)
