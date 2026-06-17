# 每个 archetype 的必填字段说明，注入 LLM prompt 用
ARCHETYPE_FIELD_SPECS: dict[str, str] = {
    "title-slide": '{"title": "最多18字的标题", "subtitle": "可选副标题"}',
    "title-bullets": '{"title": "最多18字", "bullets": ["要点1（≤40字）", "要点2"]}',
    "title-image": '{"title": "最多18字", "image_hint": "描述此处应放什么图片或图表"}',
    "two-column": (
        '{"title": "最多18字", "left_title": "左列标题", '
        '"left_content": "左列内容", "right_title": "右列标题", "right_content": "右列内容"}'
    ),
    "three-column": (
        '{"title": "最多18字", "col1_title": "列1标题", "col1_content": "列1内容", '
        '"col2_title": "列2标题", "col2_content": "列2内容", '
        '"col3_title": "列3标题", "col3_content": "列3内容"}'
    ),
    "product-comparison-2up": (
        '{"title": "最多18字", "left_title": "左方案名", '
        '"left_bullets": ["左要点1"], "right_title": "右方案名", "right_bullets": ["右要点1"]}'
    ),
    "process-flow": (
        '{"title": "最多18字", "steps": [{"title": "步骤标题", "description": "步骤描述（≤40字）"}]}'
    ),
    "cards-row": (
        '{"title": "最多18字", "cards": [{"title": "卡片标题", "content": "卡片内容（≤40字）"}]}'
    ),
    "quote-highlight": '{"quote": "引用文字（≤40字）", "attribution": "来源或署名（可选）"}',
    "content-placeholder": '{"title": "最多18字", "placeholder_hint": "此处建议放置XXX图表/架构图"}',
    "section-divider": '{"title": "最多18字的章节标题", "subtitle": "可选副标题"}',
}
