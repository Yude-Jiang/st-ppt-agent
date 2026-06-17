from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ArchetypeEnum(str, Enum):
    TITLE_SLIDE = "title-slide"
    TITLE_BULLETS = "title-bullets"
    TITLE_IMAGE = "title-image"
    TWO_COLUMN = "two-column"
    THREE_COLUMN = "three-column"
    COMPARISON_2UP = "product-comparison-2up"
    PROCESS_FLOW = "process-flow"
    CARDS_ROW = "cards-row"
    QUOTE_HIGHLIGHT = "quote-highlight"
    CONTENT_PLACEHOLDER = "content-placeholder"
    SECTION_DIVIDER = "section-divider"


# 用户切换 archetype 时，只允许切换到兼容项（字段结构相近）
ARCHETYPE_COMPAT: dict[str, list[str]] = {
    "title-slide": ["section-divider"],
    "title-bullets": ["two-column", "quote-highlight"],
    "title-image": ["content-placeholder", "title-bullets"],
    "two-column": ["title-bullets", "product-comparison-2up"],
    "three-column": ["cards-row"],
    "product-comparison-2up": ["two-column"],
    "process-flow": ["cards-row", "three-column"],
    "cards-row": ["three-column", "process-flow"],
    "quote-highlight": ["title-bullets", "section-divider"],
    "content-placeholder": ["title-image", "title-bullets"],
    "section-divider": ["title-slide", "quote-highlight"],
}


class Submission(BaseModel):
    text: str = Field(..., min_length=1)
    target_slides: int | None = Field(None, ge=1)


class SlidePlanItem(BaseModel):
    order: int
    archetype: ArchetypeEnum
    content_fields: dict[str, Any]
    user_edited: bool = False

    @field_validator("content_fields")
    @classmethod
    def validate_content(cls, v: dict) -> dict:
        title = v.get("title", "")
        if len(title) > 18:
            raise ValueError(f"标题超过18字: {len(title)}")
        for key in ("bullets", "left_bullets", "right_bullets"):
            items = v.get(key, [])
            if len(items) > 5:
                raise ValueError(f"{key} 超过5条: {len(items)}")
            for b in items:
                if len(str(b)) > 40:
                    raise ValueError(f"bullet 超过40字")
        return v


class SlidePlan(BaseModel):
    status: str = "draft"
    items: list[SlidePlanItem] = Field(..., min_length=1)


class GeneratedDeck(BaseModel):
    gcs_path: str
    download_url: str
    expires_at: datetime


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    DRAFT = "draft"
    RENDERING = "rendering"
    DONE = "done"
    FAILED = "failed"


class Task(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    submission: Submission
    slide_plan: SlidePlan | None = None
    generated_deck: GeneratedDeck | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
