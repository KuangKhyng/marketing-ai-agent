"""Content planning domain and transactional SQLite repository."""
from contextlib import contextmanager
from datetime import date, datetime, timezone
from enum import Enum
import logging
import sqlite3
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from src.config.settings import PROJECT_ROOT

DB_PATH = PROJECT_ROOT / "outputs" / "planner.sqlite3"
logger = logging.getLogger(__name__)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Stage(str, Enum):
    IDEA = "idea"
    DRAFT = "draft"
    REVIEW = "review"
    READY = "ready"
    PUBLISHED = "published"


class Channel(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


class PlanFields(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    objective: str = Field(default="", max_length=4000)
    brand: str = Field(default="", max_length=160)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def date_range(self):
        if not 0 <= (self.end_date - self.start_date).days <= 365:
            raise ValueError("Khoảng thời gian phải từ 1 đến 366 ngày.")
        return self


class Revision(StrictModel):
    revision: int = Field(ge=1)


class EditPlan(PlanFields, Revision):
    pass


class TaskFields(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    brief: str = Field(default="", max_length=8000)
    channel: Channel = Channel.FACEBOOK
    owner: str = Field(default="", max_length=120)
    due_date: date | None = None
    status: Stage = Stage.IDEA
    snapshot_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    piece_index: int | None = Field(default=None, ge=0)
    publication_url: HttpUrl | None = None
    archived: bool = False

    @model_validator(mode="after")
    def attachment_pair(self):
        if (self.snapshot_id is None) != (self.piece_index is None):
            raise ValueError("Chọn cả bản lưu và bài viết trong bản lưu.")
        return self


class EditTask(TaskFields, Revision):
    pass


class Task(TaskFields):
    id: str
    created_at: str
    updated_at: str


class Activity(StrictModel):
    at: str
    message: str


class Plan(PlanFields):
    id: str
    revision: int = 1
    created_at: str
    updated_at: str
    tasks: list[Task] = Field(default_factory=list)
    activity: list[Activity] = Field(default_factory=list)


@contextmanager
def database():
    connection = None
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(DB_PATH, timeout=5)
        connection.execute("CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL)")
        with connection:
            yield connection
    except (sqlite3.Error, OSError) as exc:
        logger.exception("Planner storage unavailable")
        raise HTTPException(503, "Kho kế hoạch đang bận hoặc chưa khả dụng. Vui lòng thử lại.") from exc
    finally:
        if connection is not None:
            connection.close()


def record(plan: Plan, message: str):
    plan.updated_at = now()
    plan.activity = [Activity(at=plan.updated_at, message=message), *plan.activity][:100]


def create(fields: PlanFields) -> Plan:
    plan = Plan(**fields.model_dump(), id=uuid4().hex, created_at=now(), updated_at=now())
    record(plan, "Tạo kế hoạch")
    with database() as db:
        db.execute("INSERT INTO plans VALUES (?, ?, ?)", (plan.id, plan.revision, plan.model_dump_json()))
    return plan


def get(plan_id: str) -> Plan:
    with database() as db:
        row = db.execute("SELECT payload FROM plans WHERE id = ?", (plan_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Không tìm thấy kế hoạch.")
    return Plan.model_validate_json(row[0])


def all_plans() -> list[Plan]:
    with database() as db:
        rows = db.execute("SELECT payload FROM plans").fetchall()
    return sorted((Plan.model_validate_json(row[0]) for row in rows), key=lambda p: p.updated_at, reverse=True)


def change(plan_id: str, revision: int, operation) -> Plan:
    # CAS also protects across processes. A failed operation changes no stored data.
    plan = get(plan_id)
    if plan.revision != revision:
        raise HTTPException(409, "Kế hoạch đã được cập nhật ở nơi khác. Tải bản mới trước khi sửa tiếp.")
    operation(plan)
    plan.revision += 1
    with database() as db:
        result = db.execute("UPDATE plans SET revision = ?, payload = ? WHERE id = ? AND revision = ?",
                            (plan.revision, plan.model_dump_json(), plan.id, revision))
        if result.rowcount != 1:
            raise HTTPException(409, "Có thay đổi mới trong kế hoạch. Tải lại để tránh ghi đè.")
    return plan
