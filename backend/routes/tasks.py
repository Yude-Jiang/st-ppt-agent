"""
REST endpoints for task management.
POST   /tasks
GET    /tasks/{task_id}
PATCH  /tasks/{task_id}/items/{order}
POST   /tasks/{task_id}/replan
POST   /tasks/{task_id}/confirm
POST   /tasks/{task_id}/render
"""
from __future__ import annotations
import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ValidationError

from ..models import (
    Task, TaskStatus, Submission, SlidePlan, SlidePlanItem,
    GeneratedDeck, ArchetypeEnum, ARCHETYPE_COMPAT
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Injected by main.py via set_task_store()
_tasks: dict[str, Task] = {}


def set_task_store(store: dict[str, Task]) -> None:
    global _tasks
    _tasks = store


def _get_task_or_404(task_id: str) -> Task:
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail={"error": "Task not found", "code": "NOT_FOUND"})
    return task


def _err(msg: str, code: str, status: int = 422):
    raise HTTPException(status_code=status, detail={"error": msg, "code": code})


def _touch(task: Task) -> None:
    task.updated_at = datetime.utcnow()


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

async def _run_planning(task_id: str) -> None:
    from ..planner import plan_slides
    task = _tasks.get(task_id)
    if not task:
        return
    task.status = TaskStatus.PLANNING
    _touch(task)
    t0 = time.time()
    try:
        plan = await asyncio.to_thread(
            plan_slides, task.submission.text, task.submission.target_slides
        )
        task.slide_plan = plan
        task.status = TaskStatus.DRAFT
        _touch(task)
        logger.info("planning done task_id=%s elapsed=%.2fs items=%d",
                    task_id, time.time() - t0, len(plan.items))
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error = str(e)
        _touch(task)
        logger.error("planning failed task_id=%s elapsed=%.2fs error=%s",
                     task_id, time.time() - t0, type(e).__name__)


async def _run_rendering(task_id: str) -> None:
    from ..builder.renderer import build_pptx
    from ..storage import upload_deck
    task = _tasks.get(task_id)
    if not task or not task.slide_plan:
        return
    task.status = TaskStatus.RENDERING
    _touch(task)
    t0 = time.time()
    try:
        items_dicts = [
            {"order": item.order, "archetype": item.archetype.value,
             "content_fields": item.content_fields}
            for item in task.slide_plan.items
        ]
        pptx_bytes = await asyncio.to_thread(build_pptx, items_dicts)
        gcs_path, signed_url, expires_at = await asyncio.to_thread(
            upload_deck, task_id, pptx_bytes
        )
        task.generated_deck = GeneratedDeck(
            gcs_path=gcs_path,
            download_url=signed_url,
            expires_at=expires_at,
        )
        task.status = TaskStatus.DONE
        _touch(task)
        logger.info("rendering done task_id=%s elapsed=%.2fs", task_id, time.time() - t0)
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error = str(e)
        _touch(task)
        logger.error("rendering failed task_id=%s elapsed=%.2fs error=%s",
                     task_id, time.time() - t0, type(e).__name__)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

class SubmitRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_slides: int | None = Field(None, ge=1)


@router.post("/tasks", status_code=202)
async def create_task(body: SubmitRequest):
    submission = Submission(text=body.text, target_slides=body.target_slides)
    task = Task(submission=submission)
    _tasks[task.task_id] = task
    asyncio.create_task(_run_planning(task.task_id))
    logger.info("task created task_id=%s", task.task_id)
    return {"task_id": task.task_id}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    task = _get_task_or_404(task_id)
    return task.model_dump(mode="json")


class PatchItemRequest(BaseModel):
    content_fields: dict[str, Any] | None = None
    archetype: str | None = None


@router.patch("/tasks/{task_id}/items/{order}")
async def patch_item(task_id: str, order: int, body: PatchItemRequest):
    task = _get_task_or_404(task_id)
    if not task.slide_plan:
        _err("No slide plan yet", "NO_PLAN")

    item = next((i for i in task.slide_plan.items if i.order == order), None)
    if not item:
        raise HTTPException(status_code=404, detail={"error": f"Item order={order} not found", "code": "NOT_FOUND"})

    new_archetype = item.archetype
    if body.archetype is not None:
        if body.archetype not in ARCHETYPE_COMPAT.get(item.archetype.value, []) and body.archetype != item.archetype.value:
            _err(
                f"Archetype {body.archetype} not compatible with {item.archetype.value}",
                "INCOMPATIBLE_ARCHETYPE"
            )
        try:
            new_archetype = ArchetypeEnum(body.archetype)
        except ValueError:
            _err(f"Unknown archetype: {body.archetype}", "UNKNOWN_ARCHETYPE")

    new_fields = dict(item.content_fields)
    if body.content_fields is not None:
        new_fields.update(body.content_fields)

    # Validate with Pydantic
    try:
        updated = SlidePlanItem(
            order=item.order,
            archetype=new_archetype,
            content_fields=new_fields,
            user_edited=True,
        )
    except ValidationError as e:
        _err(str(e), "VALIDATION_ERROR")

    idx = next(i for i, x in enumerate(task.slide_plan.items) if x.order == order)
    task.slide_plan.items[idx] = updated
    _touch(task)
    return updated.model_dump(mode="json")


class ReplanRequest(BaseModel):
    target_slides: int


@router.post("/tasks/{task_id}/replan", status_code=202)
async def replan_task(task_id: str, body: ReplanRequest):
    from ..planner import replan_slides
    task = _get_task_or_404(task_id)
    if not task.slide_plan:
        _err("No slide plan yet", "NO_PLAN")

    locked_items = [i for i in task.slide_plan.items if i.user_edited]

    async def _do_replan():
        t0 = time.time()
        try:
            new_plan = replan_slides(task.submission.text, body.target_slides, locked_items)
            task.slide_plan = new_plan
            task.slide_plan.status = "draft"
            task.status = TaskStatus.DRAFT
            _touch(task)
            logger.info("replan done task_id=%s elapsed=%.2fs", task_id, time.time() - t0)
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            _touch(task)
            logger.error("replan failed task_id=%s elapsed=%.2fs error=%s",
                         task_id, time.time() - t0, type(e).__name__)

    asyncio.create_task(_do_replan())
    return {"task_id": task_id, "status": "replanning"}


@router.post("/tasks/{task_id}/confirm")
async def confirm_task(task_id: str):
    task = _get_task_or_404(task_id)
    if not task.slide_plan:
        _err("No slide plan yet", "NO_PLAN")
    if task.slide_plan.status != "draft":
        _err(
            f"SlidePlan must be in draft status to confirm, current: {task.slide_plan.status}",
            "INVALID_STATE"
        )
    task.slide_plan.status = "confirmed"
    _touch(task)
    logger.info("task confirmed task_id=%s", task_id)
    return {"task_id": task_id, "status": "confirmed"}


@router.post("/tasks/{task_id}/render", status_code=202)
async def render_task(task_id: str):
    task = _get_task_or_404(task_id)
    if not task.slide_plan:
        _err("No slide plan yet", "NO_PLAN")
    if task.slide_plan.status != "confirmed":
        _err(
            f"SlidePlan must be confirmed before rendering, current: {task.slide_plan.status}",
            "INVALID_STATE"
        )
    asyncio.create_task(_run_rendering(task_id))
    logger.info("rendering triggered task_id=%s", task_id)
    return {"task_id": task_id, "status": "rendering"}


@router.get("/tasks/{task_id}/download")
async def download_deck(task_id: str):
    """Local dev fallback: serve .pptx directly (used when GCS unavailable)."""
    from pathlib import Path
    local_path = Path("/tmp/st-ppt-agent-decks") / f"{task_id}.pptx"
    if not local_path.exists():
        raise HTTPException(
            status_code=404, detail={"error": "File not found", "code": "NOT_FOUND"}
        )
    from fastapi.responses import FileResponse
    return FileResponse(
        str(local_path),
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".presentationml.presentation"
        ),
        filename=f"slides-{task_id[:8]}.pptx",
    )
