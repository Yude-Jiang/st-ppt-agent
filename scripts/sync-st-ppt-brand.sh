#!/usr/bin/env bash
# Sync st-ppt-brand skill Python builder into backend/vendor/st_ppt_brand/
# Usage: ./scripts/sync-st-ppt-brand.sh [path-to-skill]
set -euo pipefail

_has_builder() {
  local dir="$1"
  for name in build_deck.py builder.py render.py ppt_builder.py __init__.py; do
    [[ -f "$dir/$name" ]] && return 0
  done
  [[ -d "$dir/scripts" ]] && find "$dir/scripts" -maxdepth 1 -name '*.py' | grep -q . && return 0
  return 1
}

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/backend/vendor/st_ppt_brand"
SRC="${1:-${ST_PPT_BRAND_SKILL_PATH:-}}"

if [[ -z "$SRC" || ! -d "$SRC" ]]; then
  echo "Usage: $0 <path-to-st-ppt-brand-skill>" >&2
  echo "Or set ST_PPT_BRAND_SKILL_PATH to the skill directory." >&2
  echo "Example: $0 ~/.claude/skills/st-ppt-brand" >&2
  exit 1
fi

SRC="$(cd "$SRC" && pwd)"
mkdir -p "$DEST"

echo "==> Syncing st-ppt-brand skill"
echo "    from: $SRC"
echo "    to:   $DEST"

find "$DEST" -maxdepth 1 -type f -name '*.py' -delete
rm -rf "$DEST/scripts" "$DEST/assets" "$DEST/templates"

copy_if_exists() {
  local rel="$1"
  if [[ -f "$SRC/$rel" ]]; then
    cp "$SRC/$rel" "$DEST/$(basename "$rel")"
    echo "  copied $rel"
  fi
}

for name in build_deck.py builder.py render.py ppt_builder.py archetypes.py; do
  copy_if_exists "$name"
done

if [[ -d "$SRC/scripts" ]]; then
  mkdir -p "$DEST/scripts"
  cp "$SRC"/scripts/*.py "$DEST/scripts/" 2>/dev/null || true
  py_count=$(find "$SRC/scripts" -maxdepth 1 -name '*.py' | wc -l)
  if [[ "$py_count" -eq 1 ]]; then
    cp "$SRC"/scripts/*.py "$DEST/"
    echo "  flattened scripts/*.py to vendor root"
  else
    echo "  copied scripts/"
  fi
fi

for dir in assets templates; do
  if [[ -d "$SRC/$dir" ]]; then
    cp -r "$SRC/$dir" "$DEST/$dir"
    echo "  copied $dir/"
  fi
done

if [[ -f "$SRC/__init__.py" ]]; then
  cp "$SRC/__init__.py" "$DEST/__init__.py"
  echo "  copied __init__.py"
fi

date -u +"%Y-%m-%dT%H:%M:%SZ" > "$DEST/.synced-at"
echo "$SRC" > "$DEST/.skill-source"

if ! _has_builder "$DEST"; then
  echo "==> WARNING: no builder module detected after sync." >&2
  echo "    Expected build_deck.py, builder.py, or scripts/*.py with build_pptx()." >&2
  exit 1
fi

echo "==> Sync complete."
