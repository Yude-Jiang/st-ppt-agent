"""Pytest defaults: allow legacy renderer until st-ppt-brand skill is vendored."""
from __future__ import annotations

import os

os.environ.setdefault("ST_PPT_BRAND_ALLOW_LEGACY", "1")
