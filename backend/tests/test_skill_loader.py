"""Tests for st-ppt-brand skill loader integration."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from backend.builder import renderer
from backend.builder.skill_loader import (
    SkillNotFoundError,
    get_build_pptx,
    reset_cache,
    skill_root,
)


@pytest.fixture(autouse=True)
def _reset_skill_cache():
    reset_cache()
    yield
    reset_cache()


def test_build_pptx_legacy_fallback_produces_bytes():
    os.environ["ST_PPT_BRAND_ALLOW_LEGACY"] = "1"
    items = [
        {
            "order": 1,
            "archetype": "title-slide",
            "content_fields": {"title": "测试标题", "subtitle": "副标题"},
        }
    ]
    data = renderer.build_pptx(items)
    assert isinstance(data, bytes)
    assert len(data) > 1000
    assert data[:2] == b"PK"  # .pptx is a zip archive


def test_skill_not_found_without_legacy_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("ST_PPT_BRAND_ALLOW_LEGACY", raising=False)
    monkeypatch.setenv("ST_PPT_BRAND_SKILL_PATH", str(tmp_path / "missing"))
    reset_cache()
    with pytest.raises(SkillNotFoundError):
        get_build_pptx()


def test_skill_root_from_env(tmp_path, monkeypatch):
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "builder.py").write_text(
        "def build_pptx(items):\n    return b'PK\\x03\\x04mock'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ST_PPT_BRAND_SKILL_PATH", str(skill_dir))
    monkeypatch.delenv("ST_PPT_BRAND_ALLOW_LEGACY", raising=False)
    reset_cache()
    assert skill_root() == skill_dir.resolve()
    assert get_build_pptx()([]) == b"PK\x03\x04mock"


def test_vendor_dir_detected_when_populated(tmp_path, monkeypatch):
    from backend.builder import skill_loader

    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "build_deck.py").write_text(
        "def build_deck(items):\n    return b'PK\\x03\\x04vendor'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(skill_loader, "VENDOR_DIR", vendor)
    monkeypatch.delenv("ST_PPT_BRAND_SKILL_PATH", raising=False)
    monkeypatch.delenv("ST_PPT_BRAND_ALLOW_LEGACY", raising=False)
    reset_cache()
    assert skill_root() == vendor
    assert get_build_pptx()([{"order": 1, "archetype": "title-slide", "content_fields": {}}]) == b"PK\x03\x04vendor"
