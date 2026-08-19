---
name: multi-agent-pipeline
description: >
  **DEFAULT** — 大多数开发任务应使用此协同架构，但有明确逃生口：
  GLM analyzes → Kimi codes → (GLM + Kimi K3) parallel review → Default orchestrates.
  Kimi K3 负责多模态/视觉审查（browser_vision 截图对比，仅当项目含前端/图表时触发）。
  如果 pipeline 阻塞（超时、无输出、用户催），立即回退 solo。
  每次操作必须输出进度信息，防止用户误以为卡住。
triggers:
  - "多agent"
  - "协作"
  - "pipeline"
  - "让glm分析"
  - "让kimi写"
  - "多模型"
  - "multi-agent"
  - "分工"
  - "并行"
  - "开发"
  - "部署"
  - "重做"
  - "重构"
  - "实现"
---

# Multi-Agent Collaboration Pipeline

## Architecture

```
default (DeepSeek V4 Pro)  ← Orchestrator — dispatches, integrates, verifies
    │
    ├─ ① GLM 5.3   ─┬─ 代码/后端架构分析 ────────────────┐
    │               │                                      │
    │               └─ (并行) Kimi K3 → UI/视觉架构分析 ──┤
    │                                                      │
    ├─ ② Kimi K2.7 → 编写代码                              │
    │                                                      │
    ├─ ③ 并行审查 ─┬─ 3a: GLM 5.3  → 代码逻辑/安全审查 ──┤
    │              │                                       │
    │              └─ 3b: Kimi K3  → 可视化产出审查 ──────┤
    │                                                      │
    └─ ④ DeepSeek V4 → 汇总审查意见、应用修复、集成验证
```

**Kimi K3 审查触发条件**：仅当项目产出包含 HTML/CSS/SVG/图表生成代码/图片文件时触发。
纯后端 API / CLI 工具 / 单行 CSS 改动 → 跳过 Kimi K3。

## Profile Check

Before dispatching, verify profiles exist and are configured:

```bash
hermes profile list
```

Expected output should include: `default`, `glm-review`, `kimi-coder`, `kimi-ocr`.

**Verified working**:
- `glm-review` → GLM 5.3 ✅ — 代码架构分析、代码审查
- `kimi-coder` → Kimi K2.7 Coder ✅ — 代码编写（仅编码，禁用推理）
- `kimi-ocr` → Kimi K3 ✅ — UI/视觉架构分析、可视化产出审查、截图对比
- `default` → DeepSeek V4 Pro ✅ — 编排、集成、验证、最终交付

## Pipeline Steps

### Phase 1: Architecture Analysis (GLM + optional Kimi K3)

**1a — GLM 5.3: 代码/后端架构分析**（始终执行）

Send the project spec to GLM:

```bash
hermes -p glm-review chat -q "分析以下项目架构，输出每个模块需要创建的文件清单、
接口定义、数据模型、关键逻辑。不要写代码，只输出规格说明。

[粘贴架构文档或需求描述]"
```

**Expected output**: File list, API surface, data model, component tree, logic notes.

**1b — Kimi K3: UI/视觉架构分析**（仅当项目含前端/图表/图片产出时并行执行）

如果项目涉及 HTML/CSS/前端组件/图表/图片生成，**同时**派发 Kimi K3 做视觉架构分析：

```bash
hermes -p kimi-ocr chat -q "分析以下项目的 UI/视觉架构需求：

[粘贴需求中的 UI/视觉部分：页面布局、组件树、配色方案、
图表类型、交互行为、响应式要求]

输出：
1. 页面/组件清单（带层级关系）
2. 每个组件的视觉规格（布局、尺寸、配色、状态）
3. 图表/图片清单（类型、数据源、标注要求）
4. UI 与后端 API 的对接点
5. 视觉一致性检查清单"
```

GLM 和 Kimi K3 并行派发（`terminal(background=true)`），两者完成后合并为完整架构规格，再进入 Phase 2。

### Phase 2: Kimi Coder Writes Code (file by file)

**Critical**: Do NOT give Kimi the entire spec at once. Instead, GLM breaks the spec into per-file tasks. For each file, dispatch Kimi with only the context it needs:

```bash
hermes -p kimi-coder chat -q "修改文件: /path/to/file.js

当前文件内容:
[粘贴现有代码]

需要改动:
[GLM 针对这个文件的具体指示 — 改什么、加什么、删什么、注意什么]

只输出新文件的完整代码。"
```

**Parallel dispatch**: Independent files (e.g., backend route A + frontend component B) can be dispatched simultaneously via separate `terminal(background=true)` calls.

**Sequential for dependencies**: If file B depends on file A, wait for A's output before dispatching B.

### Phase 3: Parallel Review (GLM code + Kimi K3 visual)

As Kimi produces each file, route it to the appropriate reviewer. Both reviewers run in parallel.

#### 3a — GLM 5.3: Code Review（代码逻辑/安全/风格）

适用于所有代码文件（.js/.py/.ts/.go 等）。每个文件完成后立即送入 GLM 审查：

```bash
hermes -p glm-review chat -q "审查文件: /path/to/file.js

原始需求（这个文件要做什么）:
[GLM Phase 1 中针对这个文件的规格]

Kimi 写的代码:
[粘贴 Kimi 的输出]

对照需求检查: 遗漏 / 安全漏洞 / 逻辑错误 / 风格一致。输出通过或需要修改的具体位置。"
```

#### 3b — Kimi K3: Visual Review（可视化产出审查）

**触发条件**：文件类型匹配以下任一模式时才触发：
- `*.html`, `*.css`, `*.scss`, `*.less`
- `*.svg`
- 图表生成代码（含 `matplotlib`/`echarts`/`plotly`/`chart.js`/`d3` 的 `.py`/`.js` 文件）
- 图片文件（`*.png`, `*.jpg`, `*.webp`）

**工作流**：
1. **启动服务**：确保项目在本地运行（如 `:5000` / `:5173`）
2. **导航截图**：用 `browser_navigate` 打开目标页面，调用 `browser_vision` 截图
3. **派发审查**：将截图 + 原始视觉规格发给 Kimi K3：

```bash
hermes -p kimi-ocr chat -q "审查以下页面的视觉呈现：

原始视觉规格:
[Kimi K3 Phase 1b 输出的该组件的视觉规格，或设计稿描述]

当前页面截图:
[粘贴 browser_vision 返回的截图分析结果]

检查项：
1. 布局是否与规格一致（位置、大小、间距）
2. 配色是否正确
3. 文字是否可读、未被截断
4. 交互元素是否可见、可访问
5. 图表数据标注是否准确
6. 响应式/不同分辨率表现

输出：✅ 通过 / ⚠️ 需修改（具体位置+修改建议）"
```

**审查文件路由规则**：
| 文件类型 | 送 GLM 3a | 送 Kimi K3 3b |
|----------|:---------:|:-------------:|
| .py / .js / .ts / .go 后端代码 | ✅ | ❌ |
| .html / .css / .scss | ✅ | ✅（并行送两边） |
| .svg / 图片文件 | ❌ | ✅ |
| 图表生成代码 (.py/.js 含 matplotlib/echarts 等) | ✅ | ✅（GLM 查逻辑，Kimi K3 查视觉效果） |

Do NOT batch all files into one review — review each as Kimi finishes it, so fixes are small and fast.

### Phase 4: Default Integrates (DeepSeek V4)

Orchestrator (you, default profile) takes all outputs:
- Apply code fixes from GLM 3a
- Apply visual fixes from Kimi K3 3b
- Re-run the app and verify both code and visuals
- Handle wiring between modules
- Final browser_vision sanity check if Kimi K3 flagged visual issues

## ⚡ 进度输出规则（MANDATORY）

**每次操作都必须输出进度**，让用户实时看到执行状态。格式如下：

```
━━━ [Phase 1/4] 架构分析 ━━━
📤 GLM 分析代码架构... ⏳ 等待中 (12s)
📤 Kimi K3 分析 UI/视觉架构... ⏳ 等待中 (8s)
✅ GLM 返回规格说明 (5 个文件, 3 个接口)
✅ Kimi K3 返回视觉规格 (3 个页面, 2 个图表)

━━━ [Phase 2/4] Kimi 编写代码 ━━━
📝 文件 1/5: routes/auth.js → Kimi 正在生成...
✅ 文件 1/5 完成 (156 行)
📝 文件 2/5: templates/index.html → Kimi 正在生成...
✅ 文件 2/5 完成 (89 行)

━━━ [Phase 3/4] 并行审查 ━━━
🔍 [GLM] 审查 routes/auth.js → 检查中...
🔍 [Kimi K3] 审查 templates/index.html → 启动服务截图...
✅ [GLM] routes/auth.js 通过
✅ [Kimi K3] index.html 视觉审查通过（布局/配色/可读性 OK）
📤 [Kimi K3] 截图对比 chart.png → 派发审查...
⚠️ [Kimi K3] chart.png 发现 2 个视觉问题（图例重叠、Y轴标签截断）

━━━ [Phase 4/4] Default 集成验证 ━━━
🔧 修复 GLM 代码问题: 0 处
🔧 修复 Kimi K3 视觉问题: 2 处（图例间距 + Y轴标签宽度）
🚀 重启服务验证...
📸 最终 browser_vision 复查...
✅ 全部完成！服务运行在 :5000
```

**关键原则**：
- 每个 Phase 开始前输出分隔线和阶段名
- 每次向 Agent 发送 prompt 时输出 `📤 正在发送...`
- 每次收到 Agent 回复时输出 `✅ 完成` 或 `❌ 失败`
- 如果某个阶段超过 30 秒没有输出，主动输出 `⏳ 等待中...` 防止用户以为卡住
- **30s 轮询是硬规则**：Agent 派发后，每 30 秒 `process(action='poll')` 一次并报告状态
- GLM 等待轮询示例：
  ```
  ⏳ GLM 初始化中 (41s)...  
  ⏳ GLM 深度思考中 (117s)...  
  🔄 GLM 写作中 (322s, 正在推导 Rank 法排列分解)...
  ✅ GLM 返回 (5m30s)
  ```
- 禁止静默执行——没有进度输出 = 用户不知道发生了什么

## When To Use

| Task size | Use pipeline? | Why |
|-----------|---------------|-----|
| **用户急了/催了/怒了** | ❌ **立刻 Solo** | 速度 > 架构，零依赖直接出活 |
| Single file, <50 lines | ❌ Solo | 开销不划算 |
| CRUD module (3-5 files) | ❌ Solo | Context 传递成本 > 收益 |
| Full-stack feature (backend + frontend) | ✅ Pipeline | 独立模块，接口清晰；含前端时启用 Kimi K3 |
| Architecture review of existing codebase | ✅ Phase 1 only | GLM 分析（+ Kimi K3 如果有前端），default 执行 |
| **Full-stack rewrite (10+ files)** | ⚠️ **Phase 1 only** | Phase 2-3 context 成本过高；按 spec solo |
| Quick bug fix | ❌ Solo | 一个改动一个文件 |
| **UI 重设计 / 图表生成** | ✅ Pipeline + Kimi K3 | Kimi K3 Phase 1b 视觉分析 + Phase 3b 截图审查 |
| **纯后端 API / CLI** | ✅ Phase 1 + Solo | 无视觉产出，跳过 Kimi K3，GLM 分析后 default 编码 |

## Pitfalls

### 🔴 优先级 #0：先澄清需求再写代码

用户提出模糊需求时，**必须先问清楚再动手**。禁止想当然地直接编码。

**怎么做**：用 `clarify` 工具把关键决策点逐个确认：
- 技术栈选型（前后端分离 vs 纯前端 vs 桌面应用）
- 核心功能范围（做哪些、不做哪些、优先级）
- API / 密钥来源（用户提供 vs 本地 mock vs 设置界面填入）
- 部署形态（浏览器打开 vs 命令行 vs 服务部署）

**教训（2026-07-11）**：用户说"用 kimi ocr 提取颜色"，我直接搭 Flask backend + 写代码，用户打断"你还没问我的需求呢"。后续通过 4 轮 clarify 才确认：3 种取色模式全做、API Key 设置界面填入、前后端分离、Canvas 预览。先问 2 分钟 > 推倒重来 20 分钟。

### GLM Phase 1 30s 硬超时 → 主动切 Solo

GLM Phase 1 有时卡在 `Initializing agent...` 超过 3 分钟不产出。**30 秒无输出就主动降级**，不等用户催：

```
⏳ GLM 初始化中 (6s)...
⏳ GLM 初始化中 (36s)... → 触发 30s 阈值 → 切 Solo
━━━ 不等了，先写代码 ━━━
```

**做法**：30s 内没收到第一段分析文字，直接 kill GLM 进程，通知用户"不等了先写代码"，然后按自己的架构理解 Solo 编码。不要默默轮询等用户发怒。

详见 `references/glm-agent-notes.md`。

### 🔴 优先级 #1：用户怒了 → 立刻简化

当用户说"别管那个了"、"我就要X"、"我操你的"——**立即停下手头所有东西**，把服务做成零依赖、零认证、直接可用的状态：

- 去掉所有外部服务依赖（登录代理、Redis、第三方 API）
- 去掉认证（端点直接暴露）
- 前端去掉登录页
- **速度 > 架构**：用户要的是能用的东西，不是完美的架构

本次 Dashboard 重做教训：花了 90% 时间修排期系统登录代理，用户一句话"别他妈管"，30 秒去掉登录后全通了。

### 🔴 Kimi K3 视觉审查注意事项

- **服务必须先跑起来**：Kimi K3 用 `browser_vision` 截图，不是读源码。Phase 3b 前确保 `localhost:<port>` 可访问。
- **截图时机**：等页面完全渲染后再截图（等 1-2s 让 CSS 动画/图表渲染完成），否则可能拍到空白页。
- **截图对比基准**：每次审查都要提供"期望的样子"——来自 Phase 1b Kimi K3 的视觉规格，或用户提供的设计稿/参考图。
- **图表数据验证**：Kimi K3 能检查图表标注是否清晰、图例是否重叠，但**不能**验证图表数据值是否正确——数据正确性由 GLM 3a 审查图表生成代码负责。
- **Kimi K3 超时**：视觉审查涉及截图 + 传输，比纯文本审查慢。设置 ≥180s timeout。
- **审查粒度**：Kimi K3 审查的是**页面级**视觉呈现（布局/配色/可读性），不是像素级还原。不要为 1px 偏差反复修改。

### Kimi 代码常见 bug

Kimi K2.7 固定产出以下 bug，Phase 3 审查不如 Phase 4 直接 grep 修复：

- `const { prisma } = require` — 应 `const prisma =`（解构错误）
- `req.query.day` — 应是 `req.query.days`
- `$queryRaw` + `${var}` 插值 — 应 `$queryRawUnsafe`
- `module.exports = fn` — 应 `{ fn }`（调用方用 `.fn` 访问时）
- Prisma model 名下划线 — Prisma 自动 camelCase：`prisma.codeChange` 非 `prisma.code_changes`

详见 `references/kimi-coder-pitfalls.md`。

### Prisma + SQLite DateTime 类型冲突

手动建表时 `createdAt` 列是 TEXT，Prisma schema 用 `DateTime` 会报 `Inconsistent column data: Could not convert value ... to type DateTime`。**修复**：schema 改 `String`，传 `.toISOString()`。

详见 `references/prisma-sqlite-datetime.md`。

### Prisma 中文 UTF-8 编码丢失（Windows SQLite）

`prisma.$queryRawUnsafe` 参数化传中文时在 Windows SQLite 下产生乱码。修复：用 `$executeRawUnsafe` 将值直接嵌入 SQL（escape 单引号）。

详见 `references/prisma-utf8-encoding.md`。
- **Delegation 验证死循环**: `hermes -p` 子进程经常卡在验证阶段（装依赖、跑测试）但文件其实已写对且 `node --check` 通过。看到文件已写入就 kill 子进程。
- **GLM 长 prompt 分裂法（2026-07-02 新增）**: 单 prompt >500 words 时 GLM 频繁卡 Initializing agent 超过 3 分钟不出内容。**做法**：将复杂问题拆成 4-5 个子问题，每个 ≤300 words，用 `terminal(background=true)` 并行派发。实测：MCM Problem C 拆成 T1-T4 四个 prompt, T3 2m47s 完成, T4 2m15s 完成，而合并版 prompt 3 分钟仍无输出。**注意**：子 prompt 之间不要引入依赖（不要写"基于 T1 的结果..."），让它们完全独立。
- **GLM 长 prompt 超时**: GLM 5.3 对含代码库探索的 prompt 频繁超时。解决方案：(a) Prompt 中写明"不要探索代码库"；(b) 所有上下文内联到 prompt；(c) Prompt 控制在 300 words 内。详见 `references/glm-agent-notes.md`。
- **GLM 天然慢**：GLM 5.3 处理速度比 DeepSeek/Kimi 慢 40-80%（实测 ~4.5min vs ~2.5min）。并行派发时设置 ≥300s timeout，每条 prompt 控制在 300 words 以内时完成时间可降至 2-3min。不要误判为卡住。
- **default 可并行派发**：即使当前会话就是 default，也可 `hermes chat`（无 -p）启动新 default 实例做并行工作。
- **Zombie 端口占用**: `hermes -p` 后台进程 kill 后残留 node.exe 占端口。每次启动前 `netstat -ano | grep ':PORT '` 检查并用 `taskkill //F //PID <pid>` 清除。
- **Context cost ceiling**: For rewrites touching 10+ files that share state (auth, DB schema, API contracts), each sub-agent in Phase 2 would need ALL files as context (~2000+ lines). The paste-cost exceeds the parallelism benefit. Fall back to Phase 1 only, then code solo.
- **Partial pipeline is valid**: Running only Phase 1 (GLM → spec) and skipping Phase 2-3 is a supported pattern.
- **Silent catch**: `catch { return []; }` in data-fetching code hides failures. Always surface errors. For FullCalendar, use callback mode. See `references/ui-bug-patterns.md`.
- **Verification rate-limiters**: Restart backend before running verification. See `references/verification-script-pitfalls.md`.
- **numpy 矢量化的 safe_diff 防除零**：`np.where` 会先求值所有分支，mask 排除的零值处仍触发除法警告。用 `safe_diff = np.where(diff < eps, 1.0, diff)` 替换。详见 `references/numpy-safe-divide-hls.md`。

## Reference Files

- `references/architecture-landscape.md` — **三套架构全景图**：math-brainstorm / brute-force-think / 本 Pipeline 的串联关系、角色矩阵、架构选择速查
- `references/glm-agent-notes.md` — GLM prompt size/timeout patterns, port zombie cleanup
- `references/kimi-coder-pitfalls.md` — Prisma import bug, $queryRaw misuse, export shape, verification loops
- `references/kimi-vision-image-processing.md` — **Kimi K3 视觉审查模式**：图片编码、截图对比 prompt 模板、视觉审查检查清单、成本优化
- `references/mcm-multi-agent-lessons.md` — MCM实战: 3-agent并行脑暴性能数据, GLM长prompt分裂法, Kimi编码卡死, 用户急了→solo
- `references/fpdf2-unicode-pitfalls.md` — fpdf2生成PDF时Helvetica字体不支持希腊字母/数学符号的替代方案
- `references/pipeline-example-auth-reset.md` — concrete GLM→Kimi→verify example
- `references/sms-registration-pattern.md` — dual-mode SMS service
- `references/ui-bug-patterns.md` — silent catch, FullCalendar failureCallback
- `references/verification-script-pitfalls.md` — rate-limiter reset, Python and/or short-circuit
- `references/llm-json-extraction.md` — LLM JSON 安全提取：三层容错 `_extract_json`、Prompt 强化技巧、空响应按 finish_reason 分类报错
- `references/flask-image-upload.md` — Flask 大图上传最佳实践：MAX_CONTENT_LENGTH、PIL 像素上限、自动缩放 save_upload、413 handler、格式校验
- `references/flask-canvas-image-tool-architecture.md` — Flask+Canvas 图像工具架构模板：端点设计、实时预览防抖、左右对比 Canvas、内存存储、验证模式
- `references/kimi-vision-visual-review-checklist.md` — **NEW** Kimi K3 可视化产出审查清单：布局/配色/可读性/图表标注/响应式的逐项检查模板
- `references/kimi-k3-phase1b-ui-spec-template.md` — **NEW** Kimi K3 Phase 1b UI 视觉规格输出模板：页面树、组件规格表、图表清单、交互状态矩阵
