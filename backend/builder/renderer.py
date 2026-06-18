"""Render SlidePlan items to .pptx via st-ppt-brand skill builder."""
from __future__ import annotations

from typing import Any

from .skill_loader import get_build_pptx


def build_pptx(items: list[dict[str, Any]]) -> bytes:
    """Render a list of SlidePlanItem dicts to .pptx bytes."""
    return get_build_pptx()(items)
