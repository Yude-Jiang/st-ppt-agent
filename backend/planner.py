import json
import logging
import os
import time
from typing import Any

from openai import OpenAI
from .models import SlidePlan, SlidePlanItem, ArchetypeEnum, ARCHETYPE_COMPAT
from .builder.skill_loader import get_archetype_field_specs

ARCHETYPE_FIELD_SPECS = get_archetype_field_specs()

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "placeholder"),
    base_url="https://api.deepseek.com"
)

ARCHETYPE_LIST = "\n".join([
    f"- {name}: {spec}"
    for name, spec in ARCHETYPE_FIELD_SPECS.items()
])

SYSTEM_PROMPT = f"""你是一个专业的 PPT 规划师，将用户提供的文案拆解为幻灯片分页规划。

可用的 archetype 列表（必须从这11个中选择，不能使用其他值）：
{ARCHETYPE_LIST}

字数限制（必须严格遵守）：
- 标题（title字段）：最多18字
- 单条 bullet：最多40字
- 单页 bullet 条数：最多5条

输出格式：纯 JSON 数组，不要包含任何解释或 markdown 代码块。
每个元素格式：
{{
  "order": 1,
  "archetype": "archetype名称",
  "content_fields": {{...}}
}}

第一张幻灯片必须是 title-slide 类型。
最后一张幻灯片建议是 section-divider 类型表示结束。
"""


def _parse_items(raw_json: str) -> list[SlidePlanItem]:
    """Parse and validate JSON array into SlidePlanItems."""
    # Strip markdown code blocks if present
    text = raw_json.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data)}")

    items = []
    for item_data in data:
        item = SlidePlanItem(**item_data)
        items.append(item)
    return items


def plan_slides(text: str, target_slides: int | None) -> SlidePlan:
    """Call DeepSeek to generate a SlidePlan. Retries up to 3 times."""
    slides_hint = f"\n请规划约 {target_slides} 张幻灯片。" if target_slides else ""
    user_msg = f"请将以下文案拆解为幻灯片分页规划：{slides_hint}\n\n{text}"

    last_error = None
    for attempt in range(3):
        t0 = time.time()
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3,
            )
            elapsed = time.time() - t0
            raw = response.choices[0].message.content or ""
            items = _parse_items(raw)
            logger.info("plan_slides attempt=%d elapsed=%.2fs items=%d",
                        attempt + 1, elapsed, len(items))
            return SlidePlan(status="draft", items=items)
        except Exception as e:
            last_error = e
            elapsed = time.time() - t0
            logger.warning("plan_slides attempt=%d failed elapsed=%.2fs error=%s",
                           attempt + 1, elapsed, type(e).__name__)

    raise RuntimeError(f"plan_slides failed after 3 attempts: {last_error}") from last_error


def replan_slides(
    text: str,
    target_slides: int,
    locked_items: list[SlidePlanItem],
) -> SlidePlan:
    """Replan slides, preserving locked (user_edited) items."""
    locked_orders = {item.order for item in locked_items}
    need_count = target_slides - len(locked_items)

    locked_summary = "\n".join([
        f"  位置 {item.order}: archetype={item.archetype.value}, "
        f"title={item.content_fields.get('title', '(无标题)')}"
        for item in sorted(locked_items, key=lambda x: x.order)
    ])

    user_msg = (
        f"请将以下文案拆解为幻灯片分页规划，共需 {target_slides} 张幻灯片。\n\n"
        f"以下位置已由用户锁定，请勿生成（你只需生成其余 {need_count} 张）：\n"
        f"{locked_summary}\n\n"
        f"请为其余位置（非上述 order 值）生成内容，order 值从1到{target_slides}中选择未锁定的位置。\n\n"
        f"文案内容：\n{text}"
    )

    last_error = None
    for attempt in range(3):
        t0 = time.time()
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3,
            )
            elapsed = time.time() - t0
            raw = response.choices[0].message.content or ""
            new_items = _parse_items(raw)
            # Filter out any items that conflict with locked orders
            new_items = [i for i in new_items if i.order not in locked_orders]
            all_items = list(locked_items) + new_items
            all_items.sort(key=lambda x: x.order)
            logger.info("replan_slides attempt=%d elapsed=%.2fs total_items=%d",
                        attempt + 1, elapsed, len(all_items))
            return SlidePlan(status="draft", items=all_items)
        except Exception as e:
            last_error = e
            elapsed = time.time() - t0
            logger.warning("replan_slides attempt=%d failed elapsed=%.2fs error=%s",
                           attempt + 1, elapsed, type(e).__name__)

    raise RuntimeError(f"replan_slides failed after 3 attempts: {last_error}") from last_error
