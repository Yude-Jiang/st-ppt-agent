# Project Init Skill

## 触发
用户说 "初始化项目"、"init"、"/init" 时触发。每个项目仅在首次启动时使用一次。

## 目的
确保三类 Context 文件（DOMAIN.md、CLAUDE.md、smoke-test.sh）从骨架变为可用状态，
形成 agent 的"逻辑底座 + 边界指令 + 安全绳"，才允许进入 Phase 2/3。

## 前置条件检查

### Check 1: 探索文件是否存在
扫描 `docs/explorations/` 目录：
- 如果有 `.md` 文件 → 读取最新一份，提取 DECISION LOG
- 如果为空 → 提示用户：
  "探索文件不存在。请先完成 Phase 1 EXPLORE（在 Cursor 中用多模型探讨需求），
   将结果保存到 docs/explorations/{date}-{slug}-exploration.md，再运行 /init。
   需要我生成一份探索模板吗？"
  如果用户说"是" → 生成模板（见下方）到 docs/explorations/ → 停止，等用户填写后再次 /init

### Check 2: DECISION LOG 关键项是否已确认
读取探索文件中的 DECISION LOG 段落，检查以下必选项是否已勾选 `[x]`：
- [ ] 确认 MVP scope
- [ ] 确认技术路径
- [ ] 确认验收标准
未全部勾选 → 提示用户补全后再 /init

## 执行步骤

所有步骤均为"生成草稿 → 等用户确认 → 再进入下一步"模式。

### Step 1: 填充 DOMAIN.md

读取探索文件，生成以下内容填充 DOMAIN.md 中的占位符：

1. **核心实体 erDiagram**（mermaid 格式）
   - 从探索文件中的领域描述提取实体和关系
   - 每个实体至少标注 2-3 个关键属性

2. **业务规则**
   - 从 DECISION LOG 和探索讨论中提取不可违反的规则
   - 每条规则用"必须/不得/当…时"句式，确保无歧义

3. **术语表**
   - 从探索文件中出现的专业术语提取
   - 中文术语 + 英文术语 + 定义 + 代码中的命名

4. **数据边界**
   - 数据源列表及可信度
   - 更新频率
   - 已知数据质量问题

输出后提示：**"DOMAIN.md 已生成，请审阅。确认请回复 ok，需要修改请说明。"**

### Step 2: 填充 CLAUDE.md

读取 DOMAIN.md（刚确认的版本）+ 探索文件，填充 CLAUDE.md 中的待填段落：

1. **项目信息**
   - 项目名称和一句话描述
   - 部署目标（Cloud Run service name、region、project）
   - 技术栈（从探索文件的技术选型提取）
   - 线上 URL（留空，部署后填）

2. **架构概览**
   - 从 TDD 或探索文件推导主要模块和职责
   - 关键文件路径

3. **代码规范**
   - 根据技术栈选择对应规范模板：
     - React+Vite → 组件目录规范、Tailwind 约束
     - Flask/Express → route 文件按资源拆分
     - Python 脚本 → scripts/{source}/ 目录规范
   - 硬性规则：单文件不超过 300 行

4. **已知约束**
   - 通用约束已有（port 8080、Firestore 大陆不可用等），保留
   - 追加项目特定约束（从探索文件的"坑"段落提取）

5. **常用命令**
   - dev/build/test/deploy 命令（从技术栈推导）

输出后提示：**"CLAUDE.md 已填充，请审阅。确认请回复 ok。"**

### Step 3: 生成 smoke-test.sh

读取探索文件中的"验收标准"段落 + DOMAIN.md 的数据边界，生成冒烟测试：

1. **通用检查**（已有的骨架保留）
   - health endpoint → 200
   - 主页面加载 → 200

2. **项目特定检查**
   - 从验收标准推导：每个可自动化验证的断言变成一个 `check()` 调用
   - 从数据边界推导：如果有数据源，加数据新鲜度检查

3. **语法验证**
   - 跑 `bash -n smoke-test.sh` 确认语法正确

输出后提示：**"smoke-test.sh 已生成，请审阅。确认请回复 ok。"**

### Step 4: 完整性校验

运行以下检查清单，全部通过才算初始化完成：

```
[检查项]                                              [状态]
DOMAIN.md 存在且非空                                    □
DOMAIN.md 包含至少 1 个 mermaid erDiagram               □
DOMAIN.md 包含至少 1 条业务规则                          □
CLAUDE.md 包含项目名称                                  □
CLAUDE.md 包含部署目标（service name + region）          □
CLAUDE.md 包含技术栈                                    □
CLAUDE.md 包含代码规范段落                               □
smoke-test.sh 存在且 bash -n 语法通过                    □
smoke-test.sh 包含至少 2 个 check() 调用                 □
.claude/settings.json 存在且有 hooks 配置                □
docs/explorations/ 下有已完成的探索文件                   □
shared/api.d.ts 存在                                    □
```

- 全部 ✅ → 输出："✅ 项目初始化完成。三类 Context 文件已就绪，可进入 Phase 2 /spec"
- 有 ❌ → 列出缺失项，提示修复

### Step 5: 首次 commit

```bash
git add DOMAIN.md CLAUDE.md .claude/skills/deploy/smoke-test.sh
git commit -m "init: bootstrap Context files from exploration

- DOMAIN.md: {N}个实体, {M}条业务规则
- CLAUDE.md: 部署目标 {service-name}, 技术栈 {stack}
- smoke-test.sh: {K}个冒烟测试
- Source: docs/explorations/{filename}"
```

## 探索模板（Check 1 中用户请求时生成）

```markdown
## 探索记录: [需求名称]
日期: YYYY-MM-DD

### 核心问题
- 这个需求解决的根本问题是什么?
- 谁是第一用户?他们当前怎么绕过这个问题的?
- 做到什么程度算 MVP?什么是 V2 的事?

### 领域模型草案
- 核心实体有哪些?它们之间的关系?
- 有哪些不可违反的业务规则?
- 数据从哪来?可信度如何?

### 技术可行性
- 有哪些实现路径?各自的 tradeoff?
- 和现有技术栈冲突最小的路径?
- 已知的坑?

### 管理层视角
- ROI 怎么算?
- 能否复用到其他部门?
- 失败的最小代价?

### 模型意见汇总
| 问题 | Claude | GPT | DeepSeek | 你的判断 |
|------|--------|-----|----------|----------|
| 实现路径 | | | | **选 X** |
| 主要风险 | | | | **关注 Y** |
| MVP 边界 | | | | **先做 A** |

### DECISION LOG
- [ ] 确认 MVP scope
- [ ] 确认技术路径
- [ ] 确认验收标准
- [ ] 确认领域模型核心实体
```
