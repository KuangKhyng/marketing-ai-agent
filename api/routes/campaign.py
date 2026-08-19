from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
import logging
import uuid
import os
import pickle

from api.schemas import (
    CampaignInput, BriefEdit, StrategyFeedback,
    ContentFeedback, PipelineStatus, QuickActionRequest,
)
from api.pipeline_runner import PipelineRunner
from api.events import progress_bus
from api.cache import campaign_cache, is_cacheable

router = APIRouter()

logger = logging.getLogger(__name__)

from datetime import datetime, timedelta
from contextlib import contextmanager
from threading import Lock
from pathlib import Path
from src.config.settings import PROJECT_ROOT
from src.utils.paths import safe_join, validate_id

_SESSIONS_DIR = PROJECT_ROOT / "outputs"


# Đóng vào mỗi file state.pkl. Tăng khi schema của object trong state đổi
# (CampaignBrief, ReviewResult, CampaignContent...). File version khác bị coi
# như hết hạn — thà bắt user chạy lại còn hơn khôi phục ra object thiếu field
# rồi vỡ ở chỗ khác.
_STATE_VERSION = 2


class SessionStore:
    """
    Session store với in-memory cache + file-based persistence.

    Khi server restart, state được khôi phục từ outputs/{run_id}/state.pkl
    thay vì mất hết. TTL kiểm tra dựa trên file mtime.
    """
    def __init__(self, ttl_minutes: int = 120):
        self._cache: dict[str, PipelineRunner] = {}
        # Mốc thời gian trong memory, dùng khi không có file trên disk để soi
        # mtime (persist có thể đã thất bại). Không có nó thì session nào
        # thiếu file sẽ sống mãi trong RAM.
        self._touched: dict[str, datetime] = {}
        self._lock = Lock()
        self.ttl = timedelta(minutes=ttl_minutes)

    def set(self, run_id: str, runner: PipelineRunner):
        with self._lock:
            self._cache[run_id] = runner
            self._touched[run_id] = datetime.now()
            self._persist(run_id, runner)

    def _drop(self, run_id: str) -> None:
        self._cache.pop(run_id, None)
        self._touched.pop(run_id, None)

    def _age(self, run_id: str) -> timedelta:
        """Tuổi của session: ưu tiên mtime file, không có thì mốc in-memory."""
        state_file = self._state_path(run_id)
        if state_file.exists():
            return datetime.now() - datetime.fromtimestamp(state_file.stat().st_mtime)
        touched = self._touched.get(run_id)
        if touched is None:
            return timedelta(0)
        return datetime.now() - touched

    def get(self, run_id: str) -> PipelineRunner | None:
        with self._lock:
            # 1. Try in-memory cache first
            if run_id in self._cache:
                if self._age(run_id) > self.ttl:
                    self._drop(run_id)
                    self._state_path(run_id).unlink(missing_ok=True)
                    return None
                return self._cache[run_id]

            # 2. Try restoring from disk (server restarted)
            return self._restore(run_id)

    def __setitem__(self, run_id: str, runner: PipelineRunner):
        self.set(run_id, runner)

    def _state_path(self, run_id: str) -> Path:
        validate_id(run_id, "run_id")
        return safe_join(_SESSIONS_DIR, run_id, "state.pkl")

    def _persist(self, run_id: str, runner: PipelineRunner):
        self._touched[run_id] = datetime.now()
        path = self._state_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "wb") as f:
                pickle.dump({"version": _STATE_VERSION, "state": runner.state}, f)
        except Exception as e:
            # Không được làm crash request, nhưng phải biết: mất persist nghĩa
            # là user F5 hoặc server restart là mất phiên.
            logger.error("Không persist được session %s: %s", run_id, e)

    def _restore(self, run_id: str) -> PipelineRunner | None:
        path = self._state_path(run_id)
        if not path.exists():
            return None
        age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
        if age > self.ttl:
            path.unlink(missing_ok=True)
            return None
        try:
            with open(path, "rb") as f:
                payload = pickle.load(f)
            # File của phiên bản schema khác (hoặc format cũ, chưa có version)
            if not isinstance(payload, dict) or payload.get("version") != _STATE_VERSION:
                logger.info(
                    "Bỏ state.pkl của run %s: sai version schema (cần %s)",
                    run_id, _STATE_VERSION,
                )
                path.unlink(missing_ok=True)
                return None
            runner = PipelineRunner()
            runner.state = payload["state"]
            self._cache[run_id] = runner
            self._touched[run_id] = datetime.now()
            logger.info("Khôi phục session %s từ disk", run_id)
            return runner
        except Exception as e:
            logger.warning("Không khôi phục được session %s: %s", run_id, e)
            path.unlink(missing_ok=True)
            return None


sessions = SessionStore(ttl_minutes=120)


class RunBusyError(Exception):
    """Run này đang chạy một phase khác. Route map thành HTTP 409."""


class _RunLocks:
    """
    Khoá theo run_id, không xếp hàng.

    Dùng Lock chứ không phải asyncio.Lock vì các endpoint phase đều là `def`
    (sync) và chạy trong threadpool của AnyIO.

    Cố tình KHÔNG chờ: hai tab cùng bấm thì tab thứ hai nhận 409 ngay. Cho xếp
    hàng nghĩa là người dùng chờ xong rồi vẫn trả tiền cho hai lượt gọi LLM
    làm đúng một việc.
    """

    def __init__(self):
        self._locks: dict[str, Lock] = {}
        self._guard = Lock()

    def _lock_for(self, run_id: str) -> Lock:
        with self._guard:
            if run_id not in self._locks:
                self._locks[run_id] = Lock()
            return self._locks[run_id]

    @contextmanager
    def acquire(self, run_id: str):
        lock = self._lock_for(run_id)
        if not lock.acquire(blocking=False):
            logger.info("Từ chối chạy song song trên run %s", run_id)
            raise RunBusyError(run_id)
        try:
            yield
        finally:
            lock.release()

    def discard(self, run_id: str) -> None:
        with self._guard:
            self._locks.pop(run_id, None)


run_locks = _RunLocks()


@contextmanager
def _running(run_id: str):
    """Giữ khoá quanh một phase, và dịch lỗi bận thành 409."""
    try:
        with run_locks.acquire(run_id):
            yield
    except RunBusyError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Chiến dịch này đang chạy một bước khác. "
                           "Đợi bước đó xong rồi thử lại."
            },
        ) from e


def _save_session(run_id: str, runner: PipelineRunner):
    """Persist runner state to disk after each phase update."""
    sessions._persist(run_id, runner)


_DEV_MODE = os.getenv("ENV", "production").lower() in ("dev", "development", "local")

_USER_MESSAGES = {
    "brief_parser": "Không thể phân tích yêu cầu. Vui lòng mô tả rõ hơn và thử lại.",
    "strategist": "Không thể tạo chiến lược. Vui lòng thử lại.",
    "message_architect": "Không thể tạo message architecture. Vui lòng thử lại.",
    "channel_renderer": "Không thể tạo nội dung. Vui lòng thử lại.",
    "reviewer": "Không thể review nội dung. Vui lòng thử lại.",
}


@router.get("/{run_id}/events")
async def stream_events(run_id: str, request: Request):
    """
    SSE endpoint — stream pipeline progress events to frontend.

    Connect BEFORE making a phase POST request to receive events.
    Events: {"type": "node_start"|"node_done"|"cache_hit"|"done", "node": str, "message": str}
    Stream closes automatically when the phase completes (sentinel None).
    """
    sub = progress_bus.subscribe(run_id)

    async def generate():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    # Chờ event mà KHÔNG chiếm thread nào của threadpool.
                    # timeout để còn kịp phát keepalive và kiểm disconnect.
                    msg = await asyncio.wait_for(sub.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"  # SSE comment, giữ kết nối
                    continue

                if msg is None:  # sentinel — phase xong
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    break
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
        finally:
            # Client đi (đóng tab, mất mạng, hoặc xong) — dọn subscription,
            # không để rò rỉ và không ảnh hưởng tab khác cùng run_id.
            progress_bus.unsubscribe(run_id, sub)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _pipeline_error(state: dict) -> HTTPException:
    """Convert pipeline error into user-friendly HTTPException."""
    raw = state.get("error", "Unknown error")
    node = state.get("current_node", "")
    logger.error("Pipeline lỗi ở node %s: %s", node or "?", raw)
    user_msg = _USER_MESSAGES.get(node, "Đã xảy ra lỗi. Vui lòng thử lại.")
    detail = {"message": user_msg}
    if _DEV_MODE:
        detail["debug"] = raw
    return HTTPException(status_code=500, detail=detail)


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
        raise _pipeline_error(state)

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
    Runs Phase 2 (strategist). Checks cache first.
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    with _running(run_id):
        if edit:
            runner.update_brief_fields(edit)

        raw_input = runner.state.get("raw_input", "")
        brand_id = runner.state.get("brand_id")

        def push(event):
            progress_bus.push(run_id, event)

        # Cache key gồm cả brief (đã tính edit ở trên), nên brief khác nhau là key
        # khác nhau — không cần loại trừ trường hợp có edit nữa.
        cached_strategy = (
            campaign_cache.get_strategy(
                raw_input,
                brand_id,
                runner.state.get("brief"),
                runner.state.get("context_pack"),
            )
            if is_cacheable(runner.state)
            else None
        )
        if cached_strategy:
            runner.state["strategy"] = cached_strategy
            progress_bus.push(run_id, {"type": "cache_hit", "node": "strategist", "message": "Chiến lược được tải từ cache."})
            state = runner.state
        else:
            state = runner.phase_2_strategy(on_progress=push)
            if not state.get("error") and state.get("strategy") and is_cacheable(state):
                campaign_cache.set_strategy(
                    raw_input,
                    brand_id,
                    state.get("brief"),
                    state["strategy"],
                    state.get("context_pack"),
                )

        progress_bus.close(run_id)

        if state.get("error"):
            raise _pipeline_error(state)

        _save_session(run_id, runner)

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
    If approved, runs Phase 3 (message architect + channel renderer). Checks cache.
    If revision requested, re-runs strategist with feedback (no cache).
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    with _running(run_id):
        raw_input = runner.state.get("raw_input", "")
        brand_id = runner.state.get("brand_id")

        def push(event):
            progress_bus.push(run_id, event)

        if not feedback.approved:
            feedback_text = _compile_strategy_feedback(feedback)
            state = runner.phase_2_strategy(feedback=feedback_text, on_progress=push)
            progress_bus.close(run_id)
            _save_session(run_id, runner)

            # Sửa lại mà hỏng thì phải báo hỏng. Trả 200 kèm chiến lược cũ nguyên
            # si là nói dối người dùng rằng đã sửa xong.
            if state.get("error"):
                raise _pipeline_error(state)

            return PipelineStatus(
                run_id=run_id,
                phase="strategy_review",
                strategy=state.get("strategy"),
                cost_estimate=state["trace"].total_cost_estimate,
            )

        # Approved — check content cache. Key gồm cả strategy hiện tại, nên chiến
        # lược vừa sửa sẽ miss cache và content được sinh lại (trước đây key chỉ có
        # raw_input nên bản sửa bị bỏ qua âm thầm).
        cached = (
            campaign_cache.get_content(
                raw_input,
                brand_id,
                runner.state.get("brief"),
                runner.state.get("strategy"),
                runner.state.get("context_pack"),
            )
            if is_cacheable(runner.state)
            else None
        )
        if cached:
            runner.state["master_message"] = cached["master_message"]
            runner.state["campaign_content"] = cached["campaign_content"]
            runner.state["human_approved"] = True
            progress_bus.push(run_id, {"type": "cache_hit", "node": "channel_renderer", "message": "Nội dung được tải từ cache."})
            state = runner.state
        else:
            state = runner.phase_3_content(on_progress=push)
            if not state.get("error") and state.get("campaign_content") and is_cacheable(state):
                campaign_cache.set_content(
                    raw_input,
                    brand_id,
                    state.get("brief"),
                    state.get("strategy"),
                    state.get("master_message"),
                    state["campaign_content"],
                    state.get("context_pack"),
                )

        progress_bus.close(run_id)

        if state.get("error"):
            raise _pipeline_error(state)

        _save_session(run_id, runner)

        return PipelineStatus(
            run_id=run_id,
            phase="content_review",
            master_message=state["master_message"].model_dump() if state.get("master_message") else None,
            content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
            warnings=state.get("warnings") or [],
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

    with _running(run_id):
        def push(event):
            progress_bus.push(run_id, event)

        # Apply inline edits
        for pf in feedback.piece_feedbacks:
            if pf.edited_body:
                runner.update_content_piece(pf.piece_index, pf.edited_body)

        if not feedback.approved:
            feedback_text = _compile_content_feedback(feedback)
            state = runner.phase_3_content(feedback=feedback_text, on_progress=push)
            progress_bus.close(run_id)
            _save_session(run_id, runner)

            if state.get("error"):
                raise _pipeline_error(state)

            return PipelineStatus(
                run_id=run_id,
                phase="content_review",
                content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
                warnings=state.get("warnings") or [],
                revision_count=state.get("revision_count", 0),
                cost_estimate=state["trace"].total_cost_estimate,
            )

        # Approved — run automated review
        state = runner.phase_4_review(on_progress=push)
        progress_bus.close(run_id)
        _save_session(run_id, runner)

        return PipelineStatus(
            run_id=run_id,
            phase="final_review",
            content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
            review_result=state["review_result"].model_dump() if state.get("review_result") else None,
            warnings=state.get("warnings") or [],
            review_route=state.get("review_route"),
            revision_count=state.get("revision_count", 0),
            cost_estimate=state["trace"].total_cost_estimate,
        )

@router.post("/{run_id}/quick-action")
def quick_action(run_id: str, action: QuickActionRequest):
    """
    Sửa nhanh một piece: viết lại / đổi hook / đổi tone / ngắn hơn / dài hơn.

    Việc thật nằm ở src/nodes/quick_action.py — route không tự dựng lời gọi LLM
    nữa. Lý do: bản cũ gọi thẳng ở đây với một prompt cô lập, nên nó đi vòng
    qua toàn bộ ràng buộc brand mà generator và reviewer đều phải tuân theo.
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    with _running(run_id):
        content = runner.state.get("campaign_content")
        if content is None:
            raise HTTPException(
                status_code=409, detail={"message": "Chưa có nội dung nào để sửa."}
            )

        if action.piece_index >= len(content.pieces):
            raise HTTPException(status_code=400, detail="Invalid piece index")

        try:
            state = runner.quick_action(action.piece_index, action.action.value)
        except Exception as e:
            logger.exception("Quick action %s hỏng", action.action.value)
            raise HTTPException(
                status_code=500,
                detail={"message": "Không sửa được nội dung. Vui lòng thử lại."},
            ) from e

        _save_session(run_id, runner)

        piece = state["campaign_content"].pieces[action.piece_index]
        return {
            "piece_index": action.piece_index,
            "hook": piece.hook,
            "new_body": piece.body,
            "cta_text": piece.cta_text,
            "word_count": piece.word_count,
            "action": action.action.value,
            # Nội dung đổi thì điểm chấm cũ hết hiệu lực — UI phải cho chấm lại
            "review_invalidated": True,
            "cost_estimate": state["trace"].total_cost_estimate,
        }


@router.post("/{run_id}/retry-content", response_model=PipelineStatus)
def retry_content(run_id: str):
    """
    Sửa lại nội dung theo đúng hướng dẫn của reviewer, rồi chấm lại.

    Đây là nhánh "retry" của LangGraph (xem src/graph/workflow.py), nhưng do
    người dùng bấm thay vì tự chạy — mỗi vòng là một lượt gọi API tốn tiền.
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    with _running(run_id):
        if not runner.can_retry():
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Đã hết lượt sửa tự động. Hãy sửa tay hoặc bàn giao.",
                },
            )

        def push(event):
            progress_bus.push(run_id, event)

        state = runner.retry_content(on_progress=push)
        progress_bus.close(run_id)
        _save_session(run_id, runner)

        if state.get("error"):
            raise _pipeline_error(state)

        return PipelineStatus(
            run_id=run_id,
            phase="final_review",
            content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
            review_result=state["review_result"].model_dump() if state.get("review_result") else None,
            warnings=state.get("warnings") or [],
            review_route=state.get("review_route"),
            revision_count=state.get("revision_count", 0),
            cost_estimate=state["trace"].total_cost_estimate,
        )

@router.post("/{run_id}/approve-final", response_model=PipelineStatus)
def approve_final(run_id: str):
    """
    Final approval — format and save output.
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    with _running(run_id):
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

    validate_id(run_id, "run_id")
    run_dir = safe_join(PROJECT_ROOT / "outputs", run_id)
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


def _infer_phase(state: dict) -> str:
    """Suy ra user đang ở bước nào từ những gì state đã có."""
    if state.get("review_result") is not None:
        trace = state.get("trace")
        if trace is not None and getattr(trace, "final_status", "") == "completed":
            return "completed"
        return "final_review"
    if state.get("campaign_content") is not None:
        return "content_review"
    if state.get("strategy"):
        return "strategy_review"
    if state.get("brief") is not None:
        return "brief_review"
    return "input"


@router.get("/{run_id}", response_model=PipelineStatus)
def get_run(run_id: str):
    """
    Đọc lại trạng thái hiện tại của một run.

    Dùng khi user F5 hoặc mở lại link có ?run=<id>: frontend gọi endpoint này
    để dựng lại đúng bước đang dở, thay vì mất sạch dù server vẫn còn state.

    LƯU Ý: route này phải khai báo SAU /history, nếu không "history" sẽ khớp
    vào {run_id} và endpoint kia thành 404.
    """
    validate_id(run_id, "run_id")
    runner = sessions.get(run_id)
    if not runner or not runner.state:
        raise HTTPException(
            status_code=404,
            detail={"message": "Phiên làm việc đã hết hạn hoặc không tồn tại."},
        )

    state = runner.state
    trace = state.get("trace")

    return PipelineStatus(
        run_id=run_id,
        phase=_infer_phase(state),
        brief=state["brief"].model_dump() if state.get("brief") else None,
        strategy=state.get("strategy"),
        master_message=state["master_message"].model_dump() if state.get("master_message") else None,
        content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
        review_result=state["review_result"].model_dump() if state.get("review_result") else None,
        warnings=state.get("warnings") or [],
        review_route=state.get("review_route"),
        revision_count=state.get("revision_count", 0),
        cost_estimate=trace.total_cost_estimate if trace else 0.0,
    )


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
