# st-ppt-brand skill (vendored)

This directory holds a **synced copy** of the real `st-ppt-brand` Claude skill builder.

The app does not reimplement brand rendering here — populate this folder from your skill source:

```bash
# From repo root — pass skill directory path
./scripts/sync-st-ppt-brand.sh ~/.claude/skills/st-ppt-brand

# Or set env and run without args
export ST_PPT_BRAND_SKILL_PATH=~/.claude/skills/st-ppt-brand
./scripts/sync-st-ppt-brand.sh
```

## Expected skill layout

The loader accepts any of these:

```
st-ppt-brand/
  build_deck.py      # exports build_pptx() or build_deck()
  builder.py
  scripts/build_deck.py
  __init__.py        # exports build_pptx + optional ARCHETYPE_FIELD_SPECS
```

Or per-archetype helpers: `add_title_slide`, `add_cards_row`, `add_comparison`, `add_process_flow`, etc.

## Dev fallback

If this directory is empty, set `ST_PPT_BRAND_ALLOW_LEGACY=1` to use the temporary
`legacy_renderer.py` (not for production — does not match full ST brand spec).
