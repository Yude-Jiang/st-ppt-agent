## 探索记录: ST PPT Agent
日期: 2026-06-17

### 核心问题
- 这个需求解决的根本问题是什么?
  同事手写 ST 品牌合规 PPT 耗时且容易踩坑（logo 安全区、配色超过 2-3 色、message bar 字号不对、
  用了 SmartArt 或白底黄字等）。`st-ppt-brand` skill 已经把这些规则和 11 个 layout archetype
  编码好了，但目前只能在 Claude.ai 对话里用——同事不会用 skill，需要一个直接粘贴文案就能出
  draft 的网页工具。
- 谁是第一用户?他们当前怎么绕过这个问题的?
  ST 内部同事（市场/销售/产品线），目前手段是复制旧 deck 改文字，或从头在 PowerPoint 里画，
  容易跑出品牌规范，且每次都要重新决定排版。
- 做到什么程度算 MVP?什么是 V2 的事?
  MVP: 粘贴文案 → LLM 推荐分页方案（layout + 内容）→ **同事可对 SlidePlan 做轻量确认/微调**
  （改标题文字、删减/合并 bullet、更换某页的 layout archetype——不是完整拖拽编辑器，是结构化
  字段级的编辑）→ 同事可调整目标页数（内容密度联动）→ 生成可下载的 .pptx，使用
  `st-ppt-brand` skill 里验证过的 python-pptx builder。
  在线拖拽编辑器明确**排除**在 MVP 之外——下载后用 PowerPoint 自己调整版式细节。
  **加这层 SlidePlan 微调是经过多模型评审后追加的关键决策**：GPT 和 DeepSeek 都独立指出，
  如果生成前完全不能改，用户会陷入"生成→下载→打开发现不对→回网页重新生成"的死循环，
  这比拖拽编辑器轻得多，但能避免这个循环。
  架构图/走势图等需要配图才能说清楚的内容：**MVP 选择留白处理**——LLM 识别到原文需要图表
  时，在对应位置生成一个占位框 + 提示文字（说明这里应该放什么类型的图），同事下载后自己
  插入实际图片。MVP 不做图表/架构图的自动生成。
  V2: 在线拖拽编辑器（如果 MVP 上线后证明需求强烈）；独立于 builder 的 **brand check 环节**
  （校验 LLM 输出的文本是否过长、语义层是否合规，如标题超长、bullet 数超标、白底黄字等内容
  层问题——这是 builder 管不到的，builder 只保证几何/样式正确）；更多 layout archetype 的
  自动识别；架构图/走势图的自动生成或智能配图；历史 deck 重用/模板库。

### 领域模型草案
- 核心实体有哪些?它们之间的关系?
  - **Submission**（同事的一次提交）：原始粘贴文案、目标页数（可选，默认由 LLM 建议）
  - **SlidePlan**（LLM 拆页规划）：属于一个 Submission，状态为 `draft`（待确认）或
    `confirmed`（用户已确认，可渲染），包含若干 **SlidePlanItem**
  - **SlidePlanItem**（每项 = 一页的规划）：选用的 layout archetype + 该页内容字段
    （标题、bullets、图片占位提示等，字段结构取决于 archetype）+ 排序号。**用户可对单个
    SlidePlanItem 做字段级编辑**：改标题文字、删减/合并 bullet、更换 archetype（仅限切换为
    另一个同样能容纳该内容的 archetype，不允许凭空生成新内容）。每次编辑后该 item 标记为
    `user_edited`，重新生成 SlidePlan 时跳过/保留用户已编辑的项，不应覆盖。
  - **GeneratedDeck**：由 `confirmed` 状态的 SlidePlan 渲染出的 .pptx 文件（存储路径/下载链接）
  - 关系：一个 Submission → 一个（或多个修订版）SlidePlan → 一个 GeneratedDeck
- 有哪些不可违反的业务规则?
  - layout 的选用必须来自 `st-ppt-brand` skill 的 11 个 archetype，不允许 LLM 发明新版式
  - 最终页数由用户确认的数字为准；如果用户指定页数少于 LLM 初次建议，必须把内容**合并/压缩**
    进更少的页（允许信息密度变高），不能直接截断丢内容
  - **用户对 SlidePlanItem 的手动编辑（`user_edited` 状态）在任何后续的 LLM 重新规划中必须
    被保留，不能被覆盖** —— 这是为了避免 GPT/DeepSeek 都指出的"用户改了又被 AI 重新生成抹掉"
    问题
  - 配色、字体、message bar 规则等品牌约束直接复用 skill 里 `brand-spec.md` / `layout-rules.md`
    的规则，不在这个项目里重新定义一份。**MVP 阶段品牌合规仅由 python-pptx builder 的几何/
    样式规则保证**（颜色、字号、message bar 位置等代码层强制）；**语义层合规检查（标题是否
    过长、bullet 数是否超标等内容层问题）明确推迟到 V2**，MVP 不做独立的 brand check 环节
  - 原文需要图表/架构图才能说清楚的内容：LLM 识别后生成**占位框 + 提示文字**（说明应放什么
    类型的图，例如"此处建议放置产品架构图"），不在 MVP 阶段自动生成或匹配图片
  - 生成的 .pptx 不在线拖拽编辑；交付物是可下载文件，配合 SlidePlan 阶段的结构化微调
  - LLM 拆页规划的输出必须是强 Schema（建议用 Pydantic 校验），每个 archetype 对应的必填
    字段必须在 prompt 中明确列出（例如选了 `product-comparison-2up` 就必须输出
    `left_title/left_bullets/right_title/right_bullets`），缺字段时触发轻量重试而非直接报错
  - LLM 拆页规划阶段建议设置字数熔断（如标题≤15字、单条 bullet≤40字、单页 bullet≤4条），
    避免生成内容在 python-pptx 渲染时溢出文本框，压坏 message bar 或logo 安全区
- 数据从哪来?可信度如何?
  - 唯一输入是同事粘贴的自由文本（产品/技术文案），无外部数据源
  - LLM 拆页规划结果需要同事确认（`confirmed` 状态）才能进入渲染，确认前的版本不算"已交付"状态
  - 同事粘贴的内容可能涉及未公开产品/客户信息，需要在 PRD 阶段明确：LLM API 调用的数据
    留存策略、日志是否脱敏、GeneratedDeck 文件保留多久、下载链接的访问权限范围

### 技术可行性
- 有哪些实现路径?各自的 tradeoff?
  - **路径 A（已选）**：两段式——简单内容走预设模板直填（无需 LLM，快、零成本、可预测），
    复杂/自由文本走 LLM 辅助拆页规划（灵活，能处理任意输入，但有 API 调用延迟和成本）。
    已与用户讨论确认选这条路径。
  - 路径 B：前端 pptxgenjs 直接生成，不调 LLM —— 排除，因为无法处理"同事粘贴一段自由文案，
    工具自动判断用哪些 layout"这个核心需求，规则写死在代码里灵活性不够。
  - 路径 C：纯 LLM 生成完整 pptx XML —— 排除，brand 规则（颜色/字号/几何位置）由代码强制
    比让 LLM 每次重新生成更可靠，且 `st-ppt-brand` skill 里的 python-pptx builder 已验证可用，
    应该复用而不是重新发明。
- 和现有技术栈冲突最小的路径?
  - 后端 Python（FastAPI 或 Flask）+ python-pptx，复用 `st-ppt-brand` skill 的 builder 函数
    （`add_cards_row`、`add_comparison`、`add_process_flow` 等）作为渲染层
  - LLM 调用：Claude API 做拆页规划（输出结构化 JSON：每页 layout 类型 + 内容字段）
  - 前端：React + Vite，对齐 GEO Strategic Hub 等既有项目的栈
  - 部署：Cloud Run，`st-china-ai-force` / `asia-east1`，对齐全局环境约束
- 已知的坑?
  - Cloud Run 5 分钟超时（可配置到 60 分钟，但仍有上限）：更关键的是**浏览器/前端的请求超时**
    —— fetch/axios 默认超时通常在 30-60 秒，比 Cloud Run 限制更早触发。LLM 拆页规划 + 大段
    文案处理可能超过这个时间，因此**不应使用同步阻塞的 HTTP 请求等待结果**，需要采用异步任务
    模式：提交后立即返回任务 ID，前端轮询（polling）或用 SSE 获取进度/结果
  - LLM 输出的 JSON 结构必须强约束——建议引入 Pydantic 做 Schema 校验，每个 archetype 的
    必填字段在 prompt 里明确列出。校验失败时不直接 500 报错，而是触发一次轻量重试纠错
  - "用户改页数 → 内容重新分配"需要把"目标页数"作为 LLM 第二次调用的约束条件，而不是
    简单地从已有 SlidePlan 里删几项——删页会丢内容，重新分配才能保证密度提高而不是信息缺失。
    同时**必须保留用户已手动编辑过的 SlidePlanItem**，重新规划时不能覆盖 `user_edited` 状态的项
  - LLM 内容语义风险：可能误解产品术语、擅自补充未提及的事实、把营销语气改得过重、遗漏限制
    条件。建议在 SlidePlanItem 中保留对应的原文片段引用（不是为了 MVP 一定要做，但 PRD 阶段
    要评估），方便用户在确认环节核对"没有编造、没有遗漏"
  - PPT 渲染兼容性：python-pptx 生成的文件在 Windows PowerPoint、Mac PowerPoint、网页版
    PowerPoint 中的字体/换行/图形位置可能有差异，需要在 BUILD 阶段早期用真实三端测试，
    不能只在一个环境验证

### 管理层视角
- ROI 怎么算?
  省去同事手工排版+反复被打回不合规的返工时间；统一品牌一致性，降低市场/品牌团队审核负担。
- 能否复用到其他部门?
  是——任何需要出 ST 品牌合规 PPT 的部门（销售、HR、产品线）都能用同一个工具，只是输入的
  产品/技术文案不同。
- 失败的最小代价?
  MVP 阶段如果 LLM 拆页效果不理想，同事仍可以下载生成的草稿手动调整，不是不可用，只是
  价值打折——失败代价可控。

### 模型意见汇总
| 问题 | Claude | GPT | DeepSeek | Gemini | 你的判断 |
|------|--------|-----|----------|--------|----------|
| 实现路径 | 两段式（模板直填+LLM辅助），复用 st-ppt-brand skill 的 builder | 高度赞同，建议 prompt 强制要求 archetype 对应必填字段全部输出 | 同意，但"简单直填"应限定在非常明确的输入类型（title+bullets+image list），否则都走 LLM，避免两套体验质量不一致 | _(待补)_ | **选两段式**；采纳 DeepSeek 的限定建议 |
| 在线编辑范围 | 拖拽编辑器工作量大，建议先做"下载后用 PPT 自己调" | 明智的 MVP 决策；前提是生成的 .pptx 元素不能打散成图片，否则同事没法在 PPT 里改 | 同意不做拖拽编辑，但指出"生成前不能改 SlidePlan"会导致"生成-下载-发现不对-重来"死循环 | _(待补)_ | **不做拖拽编辑器，但加一层 SlidePlan 字段级微调**（采纳 GPT+DeepSeek 共同指出的缺口） |
| layout 选择策略 | LLM 自动判断 archetype，但页数由用户确认且密度联动 | 指出"调页数"易导致 LLM 重新规划丢失细节/抹掉用户已做的修改，建议改为局部操作（合并/拆分单页）而非全局重调 | 页数压缩是可读性问题不只是技术问题，需要量化验收标准（每页最大bullet数、字数等） | _(待补)_ | **选自动判断 + 用户定页数**；采纳"保留用户已编辑项不被覆盖"的约束，全局重调与局部微调并存（详见领域模型） |
| 品牌合规边界 | （未直接讨论，builder 默认保证几何/样式层） | 提出文本溢出风险：python-pptx 不会自动 AutoFit，需要字数熔断+渲染层 Autofit 兜底 | 明确指出 builder 管不了语义层合规（标题过长、白底黄字等内容问题），建议加独立 brand check 环节 | _(待补)_ | **MVP 采纳字数熔断（技术层防溢出）；独立的语义 brand check 推迟到 V2**（用户决策） |
| 架构/超时 | （未讨论） | 指出 Cloud Run 超时之外，浏览器/前端请求超时更早触发，需要异步轮询/SSE 而非同步阻塞请求 | （未讨论） | _(待补)_ | **采纳，BUILD 阶段设计为异步任务模式** |
| 数据/隐私 | （未讨论） | （未讨论） | 提出同事粘贴内容可能涉及未公开产品/客户信息，需明确数据留存策略 | _(待补)_ | **采纳，PRD 阶段需明确 LLM 数据策略、日志脱敏、文件保留期限、下载权限范围** |
| 图表/架构图占位 | （未讨论） | 提问：原文需要配图的内容 MVP 怎么处理 | （未讨论） | _(待补)_ | **MVP 留白处理**：LLM 识别后生成占位框+提示文字，同事下载后自行补图（用户决策） |

### DECISION LOG
- [x] 确认 MVP scope — 粘贴文案 → LLM 拆页规划 → 用户对 SlidePlan 做字段级微调（改标题/删
      bullet/换 archetype）→ 用户调页数 → 生成可下载 .pptx，不含在线拖拽编辑、不含独立 brand
      check（推 V2）、图表类内容做占位留白
- [x] 确认技术路径 — 两段式生成（明确输入类型走模板直填，其余走 LLM 辅助），Python 后端 +
      python-pptx 复用 st-ppt-brand skill 的 builder，React 前端，Cloud Run 部署，异步任务
      模式（轮询/SSE，不用同步阻塞请求）
- [x] 确认验收标准 — 量化数字已确认：
      (1) 字数熔断阈值：标题 ≤18 字、单条 bullet ≤40 字、单页 bullet ≤5 条
      (2) LLM 拆页规划响应时间上限 60 秒；JSON Schema 校验失败最多重试 2 次，第 3 次失败返回错误
      (3) 调页数重新生成耗时上限 60 秒（同一 LLM 调用约束）
      (4) 数据留存策略：GeneratedDeck 文件保留 7 天；下载链接为公开 URL（无需登录，MVP 阶段可用
          带签名的 GCS URL）；日志不记录原始文案和生成内容，只记录任务 ID + 状态 + 耗时
- [x] 确认领域模型核心实体 — Submission / SlidePlan(draft|confirmed) / SlidePlanItem
      (含 user_edited 标记) / GeneratedDeck
