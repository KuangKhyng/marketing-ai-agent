"""Immutable, explicit campaign snapshots, independent of session expiry."""
import hashlib
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError

from api.routes.campaign import _running, get_run
from api.schemas import PipelineStatus
from src.config.settings import PROJECT_ROOT
from src.utils.paths import atomic_write_text, safe_join, validate_id

router = APIRouter()
logger = logging.getLogger(__name__)
LIBRARY_DIR = PROJECT_ROOT / "outputs" / "library"


class SaveRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=160)


class Snapshot(BaseModel):
    id: str
    title: str
    saved_at: str
    campaign: PipelineStatus


def _path(snapshot_id: str):
    validate_id(snapshot_id, "snapshot_id")
    return safe_join(LIBRARY_DIR, snapshot_id + ".json")


def _read(snapshot_id: str) -> Snapshot:
    path = _path(snapshot_id)
    try:
        return Snapshot.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(404, "Không tìm thấy bản lưu.")
    except (OSError, ValidationError):
        logger.exception("Cannot read snapshot %s", snapshot_id)
        raise HTTPException(503, "Chưa đọc được bản lưu. Vui lòng thử lại.")


@router.post("", response_model=Snapshot)
def save_snapshot(request: SaveRequest):
    validate_id(request.run_id, "run_id")
    title = request.title.strip()
    if not title:
        raise HTTPException(422, "Vui lòng đặt tên bản lưu.")
    # Same lock as generation: never snapshot a partially updated campaign.
    with _running(request.run_id):
        campaign = get_run(request.run_id)
        if not campaign.content or not campaign.content.get("pieces"):
            raise HTTPException(409, "Chiến dịch chưa có nội dung để lưu.")
        payload = json.dumps({"title": title, "campaign": campaign.model_dump(mode="json")},
                             ensure_ascii=False, sort_keys=True)
        snapshot_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        path = _path(snapshot_id)
        # Retrying a successful request does not create duplicate versions.
        if path.exists():
            return _read(snapshot_id)
        snapshot = Snapshot(id=snapshot_id, title=title,
                            saved_at=datetime.now(timezone.utc).isoformat(), campaign=campaign)
        try:
            atomic_write_text(path, snapshot.model_dump_json())
        except OSError:
            logger.exception("Cannot save campaign snapshot")
            raise HTTPException(503, "Chưa lưu được chiến dịch. Vui lòng thử lại.")
        return snapshot


@router.get("")
def list_snapshots():
    items = []
    if LIBRARY_DIR.exists():
        for path in LIBRARY_DIR.glob("*.json"):
            try:
                snapshot = Snapshot.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValidationError):
                logger.warning("Skipping unreadable library entry %s", path.name)
                continue
            items.append({"id": snapshot.id, "title": snapshot.title,
                          "saved_at": snapshot.saved_at, "run_id": snapshot.campaign.run_id,
                          "piece_count": len((snapshot.campaign.content or {}).get("pieces", []))})
    return sorted(items, key=lambda item: item["saved_at"], reverse=True)


@router.get("/{snapshot_id}", response_model=Snapshot)
def get_snapshot(snapshot_id: str):
    return _read(snapshot_id)


@router.get("/{snapshot_id}/download")
def download_snapshot(snapshot_id: str):
    snapshot = _read(snapshot_id)
    return Response(snapshot.model_dump_json(indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="campaign-{snapshot_id}.json"'})
