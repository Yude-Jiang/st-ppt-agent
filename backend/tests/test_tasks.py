"""
Pytest tests for task management endpoints.
Uses TestClient + mock planner to avoid real LLM calls.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.models import (
    SlidePlan, SlidePlanItem, ArchetypeEnum, Task, TaskStatus
)


@pytest.fixture
def client():
    """Create a fresh app instance with empty task store for each test."""
    from backend.main import app
    from backend.routes.tasks import set_task_store
    # Enter TestClient context first (triggers lifespan which sets main.tasks),
    # then override with a fresh empty store so tests start clean.
    with TestClient(app) as c:
        store: dict = {}
        set_task_store(store)
        c._store = store
        yield c


def _make_plan() -> SlidePlan:
    return SlidePlan(
        status="draft",
        items=[
            SlidePlanItem(
                order=1,
                archetype=ArchetypeEnum.TITLE_SLIDE,
                content_fields={"title": "测试标题", "subtitle": "副标题"},
            ),
            SlidePlanItem(
                order=2,
                archetype=ArchetypeEnum.TITLE_BULLETS,
                content_fields={"title": "功能介绍", "bullets": ["特性A", "特性B"]},
            ),
        ]
    )


def _inject_plan(client, task_id: str, plan: SlidePlan | None = None):
    """Directly inject a slide plan into the task store (bypasses LLM)."""
    task = client._store[task_id]
    task.slide_plan = plan or _make_plan()
    task.status = TaskStatus.DRAFT


# ---------------------------------------------------------------------------
# Test: POST /tasks → 202 + task_id
# ---------------------------------------------------------------------------

def test_create_task_returns_202_and_task_id(client):
    with patch("backend.routes.tasks._run_planning", return_value=None):
        # Patch asyncio.create_task to avoid running background planning
        with patch("backend.routes.tasks.asyncio.create_task"):
            resp = client.post("/api/tasks", json={"text": "产品介绍文案", "target_slides": 5})
    assert resp.status_code == 202
    data = resp.json()
    assert "task_id" in data
    assert len(data["task_id"]) > 0


# ---------------------------------------------------------------------------
# Test: GET /tasks/{task_id} → 200 with task data
# ---------------------------------------------------------------------------

def test_get_task_returns_200(client):
    with patch("backend.routes.tasks.asyncio.create_task"):
        resp = client.post("/api/tasks", json={"text": "测试文案"})
    task_id = resp.json()["task_id"]

    get_resp = client.get(f"/api/tasks/{task_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["task_id"] == task_id
    assert "status" in data


def test_get_nonexistent_task_returns_404(client):
    resp = client.get("/api/tasks/nonexistent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test: PATCH /tasks/{task_id}/items/{order} → user_edited=True
# ---------------------------------------------------------------------------

def test_patch_item_sets_user_edited(client):
    with patch("backend.routes.tasks.asyncio.create_task"):
        resp = client.post("/api/tasks", json={"text": "测试文案"})
    task_id = resp.json()["task_id"]
    _inject_plan(client, task_id)

    patch_resp = client.patch(
        f"/api/tasks/{task_id}/items/1",
        json={"content_fields": {"title": "修改后标题", "subtitle": "新副标题"}}
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["user_edited"] is True
    assert data["content_fields"]["title"] == "修改后标题"


def test_patch_item_title_too_long_returns_422(client):
    with patch("backend.routes.tasks.asyncio.create_task"):
        resp = client.post("/api/tasks", json={"text": "测试文案"})
    task_id = resp.json()["task_id"]
    _inject_plan(client, task_id)

    # Title with 19 characters (exceeds 18-char limit)
    long_title = "A" * 19
    patch_resp = client.patch(
        f"/api/tasks/{task_id}/items/1",
        json={"content_fields": {"title": long_title}}
    )
    assert patch_resp.status_code == 422


# ---------------------------------------------------------------------------
# Test: POST confirm → status=confirmed
# ---------------------------------------------------------------------------

def test_confirm_task(client):
    with patch("backend.routes.tasks.asyncio.create_task"):
        resp = client.post("/api/tasks", json={"text": "测试文案"})
    task_id = resp.json()["task_id"]
    _inject_plan(client, task_id)

    confirm_resp = client.post(f"/api/tasks/{task_id}/confirm")
    assert confirm_resp.status_code == 200
    data = confirm_resp.json()
    assert data["status"] == "confirmed"

    # Verify in GET
    get_resp = client.get(f"/api/tasks/{task_id}")
    assert get_resp.json()["slide_plan"]["status"] == "confirmed"


def test_confirm_already_confirmed_returns_422(client):
    with patch("backend.routes.tasks.asyncio.create_task"):
        resp = client.post("/api/tasks", json={"text": "测试文案"})
    task_id = resp.json()["task_id"]
    _inject_plan(client, task_id)

    client.post(f"/api/tasks/{task_id}/confirm")
    # Try to confirm again
    confirm_resp = client.post(f"/api/tasks/{task_id}/confirm")
    assert confirm_resp.status_code == 422
    assert confirm_resp.json()["detail"]["code"] == "INVALID_STATE"


# ---------------------------------------------------------------------------
# Test: POST render with draft status → 422
# ---------------------------------------------------------------------------

def test_render_with_draft_status_returns_422(client):
    with patch("backend.routes.tasks.asyncio.create_task"):
        resp = client.post("/api/tasks", json={"text": "测试文案"})
    task_id = resp.json()["task_id"]
    _inject_plan(client, task_id)
    # slide_plan.status is "draft" — should NOT be allowed to render

    render_resp = client.post(f"/api/tasks/{task_id}/render")
    assert render_resp.status_code == 422
    assert render_resp.json()["detail"]["code"] == "INVALID_STATE"


def test_render_with_confirmed_status_returns_202(client):
    with patch("backend.routes.tasks.asyncio.create_task"):
        resp = client.post("/api/tasks", json={"text": "测试文案"})
    task_id = resp.json()["task_id"]
    _inject_plan(client, task_id)
    client.post(f"/api/tasks/{task_id}/confirm")

    with patch("backend.routes.tasks.asyncio.create_task"):
        render_resp = client.post(f"/api/tasks/{task_id}/render")
    assert render_resp.status_code == 202


# ---------------------------------------------------------------------------
# Test: submit → query with same task_id (end-to-end chain)
# ---------------------------------------------------------------------------

def test_submit_then_query_same_task_id(client):
    """Verify the submit→query chain uses the same real task_id and returns submission data."""
    with patch("backend.routes.tasks.asyncio.create_task"):
        resp = client.post("/api/tasks", json={"text": "端到端链路测试文案"})
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]
    assert task_id

    get_resp = client.get(f"/api/tasks/{task_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["task_id"] == task_id
    assert data["status"] in ("pending", "planning", "draft", "rendering", "done", "failed")
    assert data["submission"]["text"] == "端到端链路测试文案"


# ---------------------------------------------------------------------------
# Test: validation — empty text and zero slides rejected at submission
# ---------------------------------------------------------------------------

def test_submit_empty_text_rejected(client):
    resp = client.post("/api/tasks", json={"text": ""})
    assert resp.status_code == 422


def test_submit_zero_slides_rejected(client):
    resp = client.post("/api/tasks", json={"text": "有效文案", "target_slides": 0})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test: archetype compatibility on PATCH
# ---------------------------------------------------------------------------

def test_patch_incompatible_archetype_returns_422(client):
    with patch("backend.routes.tasks.asyncio.create_task"):
        resp = client.post("/api/tasks", json={"text": "测试文案"})
    task_id = resp.json()["task_id"]
    _inject_plan(client, task_id)

    # title-slide → title-bullets is NOT in ARCHETYPE_COMPAT["title-slide"]
    patch_resp = client.patch(
        f"/api/tasks/{task_id}/items/1",
        json={"archetype": "title-bullets"}
    )
    assert patch_resp.status_code == 422
    assert patch_resp.json()["detail"]["code"] == "INCOMPATIBLE_ARCHETYPE"


def test_patch_compatible_archetype_ok(client):
    with patch("backend.routes.tasks.asyncio.create_task"):
        resp = client.post("/api/tasks", json={"text": "测试文案"})
    task_id = resp.json()["task_id"]
    _inject_plan(client, task_id)

    # title-slide → section-divider IS compatible; keep existing title field
    patch_resp = client.patch(
        f"/api/tasks/{task_id}/items/1",
        json={"archetype": "section-divider"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["archetype"] == "section-divider"


# ---------------------------------------------------------------------------
# Test: GET /health
# ---------------------------------------------------------------------------

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
