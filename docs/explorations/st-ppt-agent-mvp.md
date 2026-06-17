# Spec: ST PPT Agent MVP

## Problem

ST 内部同事（市场/销售/产品线）需要频繁制作品牌合规 PPT，但手工排版耗时且容易踩品牌红线（配色超标、message bar 字号错误、logo 安全区不足等）。`st-ppt-brand` skill 已将规则和 11 个 layout archetype 编码为 python-pptx builder，但目前只能在 Claude.ai 对话中使用——同事不会用 skill，需要一个直接粘贴文案就能出 draft 的网页工具。

## Goals

- [ ] 同事粘贴自由文案后，AI 自动输出分页方案（每页 layout archetype + 内容字段）
- [ ] 同事可对 SlidePlan 做字段级微调：改标题/bullet 文字、删减 bullet、更换 archetype
- [ ] 同事可指定目标页数，内容自动合并/压缩而非截断
- [ ] 用户确认 SlidePlan 后可生成并下载 ST 品牌合规 .pptx
- [ ] 前端异步轮询任务状态，不因 LLM 耗时触发浏览器超时
- [ ] 生成文件 7 天内可通过公开签名 URL 下载，无需登录

## Non-Goals

- 在线拖拽编辑器（下载后用 PowerPoint 自行调整）
- 独立的语义 brand check 环节（标题过长/白底黄字等内容层检查推迟到 V2）
- 图表/架构图自动生成或智能配图（MVP 生成占位框 + 提示文字）
- 历史 deck 重用 / 模板库
- 登录鉴权（MVP 使用带签名公开 URL）

## Proposed Solution

### 整体流程

```
用户粘贴文案 + 可选页数
    │
    ▼
POST /api/tasks → 返回 task_id (202)
    │
    ▼  （前端轮询 GET /api/tasks/{task_id}）
DeepSeek 拆页规划 → Pydantic 校验 → SlidePlan (status=draft)
    │
    ▼
前端展示 SlidePlan，用户可：
  - 编辑单项字段（标题/bullet/archetype）→ user_edited=true
  - 调整目标页数 → 触发 LLM 重新规划（保留 user_edited 项）
    │
    ▼
用户点击"确认" → SlidePlan status=confirmed
    │
    ▼
POST /api/tasks/{task_id}/render → 触发 python-pptx builder
    │
    ▼
GeneratedDeck 上传 GCS → 返回带签名 URL → 前端显示下载按钮
```

### 关键设计决策

**异步任务模式**：LLM 拆页规划可能超过浏览器默认超时（30-60s），提交后立即返回 task_id，前端每 2 秒轮询状态，状态字段为 `pending → planning → draft → rendering → done | failed`。

**DeepSeek 强 Schema 输出**：prompt 中明确列出每个 archetype 对应的必填字段，LLM 必须输出完整 JSON。Pydantic 校验失败触发最多 2 次重试，第 3 次失败返回 `failed` 状态。

**user_edited 保护**：用户手动编辑任意 SlidePlanItem 后，该项标记 `user_edited=true`。调整页数触发 LLM 重新规划时，已编辑项必须原样保留，不得覆盖。

**图表占位**：LLM 识别到原文需要图表/架构图时，输出 archetype `content-placeholder`（或在 content_fields 中设 `placeholder_hint` 字段），builder 渲染为灰色占位框 + 提示文字。

**字数熔断**：Pydantic validator 强制：标题 ≤18 字、单条 bullet ≤40 字、单页 bullet ≤5 条。超出时 LLM 需在 prompt 层约束压缩。

## Data Model Changes

基于 DOMAIN.md，无新实体，明确以下字段：

### Task（任务容器，内存/Redis，不落库）

```python
class Task(BaseModel):
    task_id: str           # UUID
    status: Literal["pending", "planning", "draft", "rendering", "done", "failed"]
    submission: Submission
    slide_plan: SlidePlan | None
    generated_deck: GeneratedDeck | None
    error: str | None
    created_at: datetime
    updated_at: datetime
```

### Submission

```python
class Submission(BaseModel):
    text: str              # 原始粘贴文案，非空
    target_slides: int | None  # 用户指定页数，None 时由 LLM 自行决定；≥1
```

### SlidePlan

```python
class SlidePlan(BaseModel):
    status: Literal["draft", "confirmed"]
    items: list[SlidePlanItem]  # 至少 1 项
```

### SlidePlanItem

```python
class SlidePlanItem(BaseModel):
    order: int
    archetype: ArchetypeEnum    # 枚举，来自 st-ppt-brand skill 的 11 个值
    content_fields: dict        # 字段结构由 archetype 决定，见下方
    user_edited: bool = False

# content_fields 示例（archetype = "title-bullets"）：
# { "title": "ST MCU 产品亮点", "bullets": ["低功耗", "高性能", "全生态"] }
# content_fields 示例（含占位）：
# { "title": "系统架构", "placeholder_hint": "此处建议放置产品架构图" }
```

### GeneratedDeck

```python
class GeneratedDeck(BaseModel):
    gcs_path: str          # gs://bucket/decks/{task_id}.pptx
    download_url: str      # 带签名公开 URL，7 天有效
    expires_at: datetime
```

## API / Interface Changes

### 后端 API

| Method | Path | 说明 | 请求体 | 响应 |
|--------|------|------|--------|------|
| POST | `/api/tasks` | 提交文案，创建任务 | `{text, target_slides?}` | `202 {task_id}` |
| GET | `/api/tasks/{task_id}` | 查询任务状态 + SlidePlan | — | `200 Task` |
| PATCH | `/api/tasks/{task_id}/items/{order}` | 编辑单个 SlidePlanItem | `{content_fields?, archetype?}` | `200 SlidePlanItem` |
| POST | `/api/tasks/{task_id}/replan` | 调整页数，触发重新规划 | `{target_slides}` | `202 {task_id}` |
| POST | `/api/tasks/{task_id}/confirm` | 确认 SlidePlan | — | `200 {status: "confirmed"}` |
| POST | `/api/tasks/{task_id}/render` | 触发渲染 | — | `202 {task_id}` |

**错误规范**：所有端点返回 `{error: string, code: string}`，不裸吞异常。400 用于参数校验失败，404 用于 task 不存在，422 用于 SlidePlan 状态不满足前置条件（如 draft 状态调用 render）。

### 前端页面

**Home 页（`/`）**
- 文案输入 textarea（placeholder 含示例文案）
- 目标页数输入（可选，数字 input，留空表示 AI 自动决定）
- 提交按钮 → 跳转到 Review 页并开始轮询

**Review 页（`/review?task_id=xxx`）**
- 轮询状态，`planning` 时显示加载态
- `draft` 时展示 SlidePlan 卡片列表，每张卡片：
  - 显示 archetype 标签 + 内容字段（可内联编辑）
  - "更换版式"下拉（仅显示兼容 archetype）
  - 编辑后卡片标注"已修改"角标
- 目标页数调整 input + "重新规划"按钮（保留已编辑项）
- "确认并生成"按钮（SlidePlan confirmed 后触发渲染）
- `done` 时显示下载按钮（带签名 URL）

### Archetype 枚举（来自 st-ppt-brand skill，不得修改）

```python
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
```

## Open Questions

- [ ] `replan` 接口触发后任务状态回退为 `planning`，前端需重新进入轮询态——确认这个 UX 是否符合预期，还是应该局部刷新（只重新规划未编辑的页）？
- [ ] 任务存储：MVP 用内存字典（重启丢失）还是 Redis（跨实例持久）？Cloud Run 单实例下内存可行，但扩容后会有问题。
- [ ] archetype 枚举的"兼容"规则：用户更换某页 archetype 时，哪些 archetype 算"兼容"（内容字段结构相近）？需要在 BUILD 阶段定义兼容矩阵，或直接允许切换任意 archetype（内容字段清空重填）。
