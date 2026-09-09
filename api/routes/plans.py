"""Human-operated editorial workflow. No publishing or paid model calls."""
import csv
from datetime import timedelta
import io
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import Field

from api import planner as store
from api.planner import Channel, EditPlan, EditTask, Plan, PlanFields, Revision, Stage, Task
from api.routes.library import get_snapshot

router = APIRouter()


class Cadence(Revision):
    channels: list[Channel] = Field(min_length=1, max_length=3)
    weekdays: list[int] = Field(default=[0, 2, 4], min_length=1, max_length=7)


def validate_task(plan, task, previous=None):
    if task.due_date and not plan.start_date <= task.due_date <= plan.end_date:
        raise HTTPException(422, "Ngày đăng dự kiến phải nằm trong khoảng thời gian của kế hoạch.")
    snapshot = None
    if task.snapshot_id:
        snapshot = get_snapshot(task.snapshot_id)
        pieces = (snapshot.campaign.content or {}).get("pieces", [])
        if task.piece_index >= len(pieces):
            raise HTTPException(422, "Bài viết không tồn tại trong bản lưu.")
        if pieces[task.piece_index].get("channel") != task.channel:
            raise HTTPException(422, "Kênh của công việc phải khớp bài viết được gắn.")
    if task.status in (Stage.READY, Stage.PUBLISHED):
        review = snapshot.campaign.review_result if snapshot else None
        if not review or review.get("review_unavailable") or not review.get("overall_passed"):
            raise HTTPException(422, "Cần gắn nội dung đã đạt kiểm duyệt trước khi chuyển sang sẵn sàng đăng.")
    if task.status == Stage.PUBLISHED:
        if previous is None or previous.status not in (Stage.READY, Stage.PUBLISHED):
            raise HTTPException(422, "Chuyển bài sang Sẵn sàng trước khi ghi nhận đã đăng.")
        if not task.publication_url:
            raise HTTPException(422, "Nhập đường dẫn bài đã đăng để ghi nhận hoàn tất.")
        if (task.snapshot_id, task.piece_index) != (previous.snapshot_id, previous.piece_index):
            raise HTTPException(422, "Đổi nội dung cần quay lại bước kiểm duyệt trước.")


@router.get("")
def list_plans():
    summaries = []
    for plan in store.all_plans():
        tasks = [task for task in plan.tasks if not task.archived]
        summaries.append({**plan.model_dump(mode="json", exclude={"tasks", "activity"}),
                          "task_count": len(tasks),
                          "published_count": sum(task.status == Stage.PUBLISHED for task in tasks)})
    return summaries


@router.post("", response_model=Plan, status_code=201)
def create_plan(request: PlanFields):
    return store.create(request)


@router.get("/{plan_id}", response_model=Plan)
def get_plan(plan_id: str):
    return store.get(plan_id)


@router.put("/{plan_id}", response_model=Plan)
def edit_plan(plan_id: str, request: EditPlan):
    def update(plan):
        if any(t.due_date and not request.start_date <= t.due_date <= request.end_date for t in plan.tasks):
            raise HTTPException(422, "Khoảng thời gian mới phải chứa ngày của tất cả công việc, kể cả bài đã ẩn.")
        for key, value in request.model_dump(exclude={"revision"}).items():
            setattr(plan, key, value)
        store.record(plan, "Cập nhật thông tin kế hoạch")
    return store.change(plan_id, request.revision, update)


@router.post("/{plan_id}/tasks", response_model=Plan)
def add_task(plan_id: str, request: EditTask):
    def update(plan):
        if len(plan.tasks) >= 500:
            raise HTTPException(422, "Mỗi kế hoạch hỗ trợ tối đa 500 công việc.")
        task = Task(**request.model_dump(exclude={"revision"}), id=uuid4().hex,
                    created_at=store.now(), updated_at=store.now())
        validate_task(plan, task)
        plan.tasks.append(task)
        store.record(plan, f"Thêm bài: {task.title}")
    return store.change(plan_id, request.revision, update)


@router.put("/{plan_id}/tasks/{task_id}", response_model=Plan)
def edit_task(plan_id: str, task_id: str, request: EditTask):
    def update(plan):
        for index, previous in enumerate(plan.tasks):
            if previous.id != task_id:
                continue
            task = Task(**request.model_dump(exclude={"revision"}), id=task_id,
                        created_at=previous.created_at, updated_at=store.now())
            validate_task(plan, task, previous)
            plan.tasks[index] = task
            store.record(plan, f"{'Ẩn bài' if task.archived else 'Cập nhật bài'}: {task.title} · {task.status.value}")
            return
        raise HTTPException(404, "Không tìm thấy công việc.")
    return store.change(plan_id, request.revision, update)


@router.post("/{plan_id}/cadence", response_model=Plan)
def create_cadence(plan_id: str, request: Cadence):
    if any(day < 0 or day > 6 for day in request.weekdays):
        raise HTTPException(422, "Thứ trong tuần phải nằm từ 0 đến 6.")
    def update(plan):
        occupied = {(t.due_date, t.channel) for t in plan.tasks if not t.archived}
        added = []
        pillars = ["Chia sẻ kiến thức", "Câu chuyện thương hiệu", "Giới thiệu sản phẩm"]
        for offset in range((plan.end_date - plan.start_date).days + 1):
            day = plan.start_date + timedelta(days=offset)
            if day.weekday() not in request.weekdays:
                continue
            for channel in dict.fromkeys(request.channels):
                if (day, channel) in occupied:
                    continue
                title = pillars[(offset // 7 + sorted(set(request.weekdays)).index(day.weekday())) % 3]
                added.append(Task(id=uuid4().hex, title=title, channel=channel, due_date=day,
                                  brief=f"Mục tiêu: {plan.objective}\nGóc nội dung: {title}. Bổ sung thông tin và bằng chứng trước khi viết.",
                                  created_at=store.now(), updated_at=store.now()))
        if len(plan.tasks) + len(added) > 500:
            raise HTTPException(422, "Lịch mẫu vượt 500 công việc. Giảm số ngày hoặc số kênh.")
        plan.tasks.extend(added)
        store.record(plan, f"Tạo lịch mẫu: thêm {len(added)} ý tưởng")
    return store.change(plan_id, request.revision, update)


def safe_csv(value):
    text = str(value or "")
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")) else text


@router.get("/{plan_id}/export")
def export_plan(plan_id: str):
    plan = store.get(plan_id)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Tên bài", "Kênh", "Ngày dự kiến", "Phụ trách", "Trạng thái", "Brief", "Bản lưu", "Bài số", "URL đã đăng"])
    for task in plan.tasks:
        if not task.archived:
            writer.writerow([safe_csv(value) for value in [task.title, task.channel.value, task.due_date,
                task.owner, task.status.value, task.brief, task.snapshot_id,
                task.piece_index + 1 if task.piece_index is not None else "", task.publication_url]])
    return Response("\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="plan-{plan.id}.csv"'})
