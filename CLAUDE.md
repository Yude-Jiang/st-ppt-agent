# ST PPT Agent

<!-- /init 填充 [方括号] 内容。手动创建时逐段填写。 -->

---

<!-- ============================================================
     PART 1: 全局规则 — TEMPLATE INHERITED
     
     本段落从 vibe-coding-template 继承,是所有项目的最高层约束。
     
     维护规则:
     - 项目中发现新的通用 learning → 先加到本项目 CLAUDE.md
     - 确认是跨项目通用的 → 同步回 template repo 的 CLAUDE.md
     - 定期(每月/每季度)用 template 的最新版本覆盖各项目的 PART 1
     
     不要在项目中修改 PART 1 的已有规则,只追加。
     项目特定的规则写在 PART 2。
     ============================================================ -->

## 协作偏好

- 反馈极简("合并"、"继续"、"还是报错"),结合 PROGRESS.md 和上下文理解,不要要求重复背景
- 回复同样简洁:直接说结论和操作,不铺垫、不重复已知信息
- 关键判断点(是否建 PR、架构选型、破坏性操作)暂停等确认;执行类操作直接做
- 解释方案时给出 reasoning 和 tradeoff,不只给"做什么"
- commit message 必须包含 WHY,不只是 WHAT
- 默认中文,技术术语保留英文(deploy、PR、workflow 等不翻译)
- 对外交付物(邮件、英文文档)用英文,主动校对术语准确性

## 模型分配规则

| 任务类型 | 推荐模型 | 说明 |
|---------|---------|------|
| 核心业务逻辑、架构设计、代码审查 | Claude (B 模型) | 不可降级 |
| 样板代码、单元测试、CRUD、格式转换 | DeepSeek (C 模型) | 省 token |
| 需求探索、领域知识、竞品调研 | Claude/Gemini (A 模型) | 在 Cursor 中使用 |
| 拿不准用哪个 | Claude (B 模型) | 安全默认值 |

## 代码规范(全局)

### 硬性规则
- 单文件不超过 **300 行**,超过必须拆分
- 每个 route 文件不超过 **5 个端点**,超过按子资源拆分
- React 组件命名 PascalCase,不超过 3 个单词
- 新文件必须符合项目特定的目录结构规范(见 PART 2),不允许自由放置
- 不使用 `any` 类型(TypeScript 项目)
- 所有 API 端点必须有错误处理,不允许裸 try-catch 吞掉错误

### 目录结构模板

**React + Vite:**
```
src/components/{ComponentName}/index.jsx
src/pages/{PageName}/index.jsx
src/store/{slice-name}.js
src/api/{resource}.js
```

**Flask / Express:**
```
server/routes/{resource}.js
server/middleware/{name}.js
server/models/{entity}.js
```

**Python 数据管道:**
```
scripts/{data-source}/fetch-{source}.py
scripts/{data-source}/transform-{source}.py
```
必须有 `--dry-run` 参数。

## 环境约束(全局)

- GCP 项目 `st-china-ai-force`,region `asia-east1`
- Cloud Run 监听 port **8080**,流式请求 **5 分钟超时**
- 大陆网络: Firestore 客户端直连**不可用**,需服务端代理或改用 BigQuery
- DeepSeek: OpenAI-compatible SDK,model ID `deepseek-chat`
- AkShare: 参数名有版本漂移,调用前先验证当前版本签名

## 跨项目 Learnings(持续累积)

<!-- 
这是整个 template 最重要的段落。
每个项目中遇到的通用教训都追加到这里,然后同步回 template repo。
格式: [日期] [来源项目] 教训内容
-->

- [2024-12] [analog-pd-dashboard] A 股财报数据是 YTD 累计,必须差减上季度得到单季值
- [2024-12] [analog-pd-dashboard] AkShare 千元单位需 ×0.1 转万元,不是 ×10000
- [2025-01] [resume-ai-screener] Firebase Anonymous Auth 需在控制台手动启用,默认关闭
- [2025-01] [resume-ai-screener] Service Worker 缓存 stale hash 导致部署后白屏,需配置 skipWaiting
- [2025-03] [mcu-competitor-dashboard] 普冉股份 stock code 是 688766 不是 688694
- [2025-03] [mcu-competitor-dashboard] STAR Market(科创板)在 AkShare 中 column 值不同于主板
- [2025-04] [geo-strategic-hub] Tailwind v4 无 typography plugin,需手动处理富文本样式
- [2025-04] [geo-strategic-hub] `@google/genai` SDK 不支持 OpenAI-compatible 接口,不能混用
- [2025-05] [geo-strategic-hub] Cloud Run 流式请求 5 分钟超时,文件操作必须串行不能并行
- [2025-05] [geo-monitoring] Recharts ResponsiveContainer 在 flex 布局中需要显式 width/height
- [2025-06] [st-newsletter] Net Income % 应改为 Net Margin % — 注意英文术语准确性
- [2025-06] [skill-radar] git worktree 多 agent 并行时 merge 顺序重要,先合基础分支

<!-- 新 learning 追加在上方,保持时间顺序 -->

---

<!-- ============================================================
     PART 2: 项目特定 — /init 填充
     
     以下内容仅适用于本项目,不回流到 template。
     ============================================================ -->

## 项目信息

- **描述**: 粘贴产品/技术文案 → AI 自动拆页规划 → 用户微调确认 → 生成可下载的 ST 品牌合规 .pptx，给 ST 内部市场/销售/产品线同事用
- **部署**: Cloud Run `st-ppt-agent` on `st-china-ai-force` / `asia-east1`
- **技术栈**: React + Vite（前端） + Python FastAPI（后端） + python-pptx（渲染层）
- **线上 URL**: [部署后填写]
- **GitHub**: https://github.com/Yude-Jiang/st-ppt-agent

## 架构概览

### 主要模块

```
frontend (React+Vite):  文案输入 → SlidePlan 展示与字段级微调 → 下载触发
backend (FastAPI):      异步任务管理（提交→轮询）、DeepSeek 调用、Pydantic Schema 校验、渲染调度
builder (python-pptx):  复用 st-ppt-brand skill 的 builder 函数，按 archetype 渲染 .pptx
storage (GCS):          存储 GeneratedDeck .pptx，带签名 URL 公开下载，7 天 TTL
```

### 关键文件

```
backend/main.py              — FastAPI 入口，任务队列，路由注册
backend/planner.py           — DeepSeek 调用 + Pydantic SlidePlan Schema 校验 + 重试逻辑
backend/builder/             — python-pptx builder 函数（从 st-ppt-brand skill 复用）
backend/models.py            — Pydantic 模型：Submission / SlidePlan / SlidePlanItem / GeneratedDeck
frontend/src/pages/Home/     — 文案输入页
frontend/src/pages/Review/   — SlidePlan 微调确认页
frontend/src/api/tasks.js    — 轮询任务状态的 API 封装
```

## 项目特定代码规范

- DeepSeek 调用必须使用 OpenAI-compatible SDK，model ID 固定为 `deepseek-chat`
- LLM 输出的拆页规划必须用 Pydantic 校验，每个 archetype 的必填字段在 prompt 中明确列出
- 前端请求拆页规划必须走异步任务模式（提交→轮询），不使用同步阻塞 fetch 等待 LLM 结果
- archetype 枚举值必须与 `st-ppt-brand` skill 中的定义完全一致，不得硬编码字符串
- builder 函数从 `st-ppt-brand` skill 复用，不在本项目中重新实现渲染逻辑

## 项目特定约束

- layout archetype 只能使用 `st-ppt-brand` skill 定义的 11 个，LLM prompt 必须附上完整枚举列表
- 字数熔断阈值（Pydantic validator 层强制）：标题 ≤18 字、单条 bullet ≤40 字、单页 bullet ≤5 条
- `user_edited=True` 的 SlidePlanItem 在任何 LLM 重新规划时必须跳过/保留，不得覆盖
- SlidePlan status 为 `draft` 时，后端不得接受渲染请求；必须 `confirmed` 才能触发 builder
- GeneratedDeck .pptx 文件：GCS 7 天 TTL，下载链接为带签名公开 URL（无需登录）
- 日志不记录原始文案和生成内容，只记录 task_id + status + 耗时
- python-pptx 生成文件需在 Windows/Mac/Web PowerPoint 三端测试，不能只验一端

## 项目已知坑

<!-- 开发中发现的坑,持续追加。跨项目通用的教训同步到 PART 1 的 Learnings。 -->
<!-- 格式: [日期] 现象 → 根因 → 修复 -->

- [2026-06] 浏览器 fetch 默认超时（通常 30-60s）比 Cloud Run 超时更早触发 → LLM 拆页规划必须异步任务模式，前端轮询而非等待单次 HTTP 响应

## 常用命令

```bash
# 开发（前端）
cd frontend && npm run dev

# 开发（后端）
cd backend && uvicorn main:app --reload --port 8080

# 构建
cd frontend && npm run build

# 测试
cd backend && pytest

# 部署
/deploy

# 状态报告
/status-report
```
