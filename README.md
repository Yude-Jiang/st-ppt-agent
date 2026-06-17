# Project Name

<!-- TODO: Replace with a one-sentence description of the project. -->

## Quick Start

```bash
# TODO: Add setup instructions
```

## Documentation

| File | Purpose |
|------|---------|
| [CLAUDE.md](./CLAUDE.md) | AI assistant constraints, architecture overview, common commands |
| [DOMAIN.md](./DOMAIN.md) | Business domain terminology and rules |
| [PROGRESS.md](./PROGRESS.md) | Session progress and task history |
| [shared/api.d.ts](./shared/api.d.ts) | Shared frontend/backend API types |
| [docs/explorations/](./docs/explorations/) | Feature specs and design explorations |

## Skills (AI Slash Commands)

| Command | Description | Phase |
|---------|-------------|-------|
| `/init` | **首次启动**：引导填充三类 Context 文件 | Gate |
| `/spec` | 生成 PRD/TDD，读取 exploration + DOMAIN.md | Phase 2 |
| `/deploy [staging\|production]` | Build, deploy, and smoke-test | Phase 4 |
| `/status-report` | 读取 PROGRESS.md + git log + 膨胀预警生成周报 | Phase 5 |

## 新项目启动流程

```
1. 从此 template 创建新 repo
   → GitHub: "Use this template" → 新 repo 名

2. Phase 1 EXPLORE（在 Cursor 中完成）
   → 用多模型探讨需求
   → 保存到 docs/explorations/{date}-{slug}.md
   → 填写 DECISION LOG 并勾选必选项

3. 回到 Claude Code，执行 /init
   → agent 引导填充 DOMAIN.md → 你审阅确认
   → agent 填充 CLAUDE.md → 你审阅确认
   → agent 生成 smoke-test.sh → 你审阅确认
   → 完整性校验通过 → 首次 commit

4. Phase 2: 执行 /spec 生成 PRD + TDD

5. Phase 3: 开始 BUILD（hooks 自动验证）

⚠️ 如果跳过 /init 直接写代码，PreToolUse hook 会拦截并提醒。
```

## MCP Servers

本模板预配置了以下 MCP server（`.mcp.json`）：

| Server | 用途 | 配置要求 |
|--------|------|---------|
| filesystem | 文件读写 | 无需额外配置 |
| github | 自动创建 PR/issue、读取 repo 信息 | 需要 GitHub PAT（见下方） |
| gcloud | Cloud Run 部署、日志查看 | 需要 `gcloud auth login` |

**配置 GitHub PAT：**
1. 前往 https://github.com/settings/tokens
2. 生成 token，权限选 `repo` + `read:org`
3. 编辑 `.mcp.json`，替换 `YOUR_GITHUB_PAT_HERE`
4. **不要提交 PAT 到 repo**，用环境变量或 `.env` 替代

## Contributing

1. Read `CLAUDE.md` and `DOMAIN.md` before making changes.
2. Run tests before opening a PR.
3. Update `DOMAIN.md` when introducing new domain concepts.
