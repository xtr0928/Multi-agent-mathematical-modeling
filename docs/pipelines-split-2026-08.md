# 项目分家说明：数模管线 vs 协同编码管线

> 2026-08-14 用户决定。整个体系拆成**两个独立管线、两个 GitHub 仓库**。
> 明天（2026-08-15）新建独立 MCM GitHub 仓库，此后两个仓库分开演进。
> 本文件是拆分执行的唯一依据；迁移动作明天做，今天不做。

---

## 0. 一句话分界

| | 协同编码管线 | 数模管线 |
|---|---|---|
| 是什么 | **通用编程执行管线**：任务分级路由 → 编码 → 门禁 → 评审 → 视觉/UI/OCR | **MCM 竞赛解题管线**：审题 → 商议建模 → 求解 → 成文 → 评审 |
| 服务对象 | 一切编码任务（含数模的重计算模块） | 数学建模竞赛（72h 窗口） |
| 依赖关系 | 不依赖数模 | **消费协同编码管线作为执行资源**（Stage 3 编码需求走 T 分级路由） |
| 仓库 | 留 Multi-Agent | 明天新建独立 MCM 仓库 |

**唯一耦合点**：数模 Stage 3 的编码需求 → 协同编码管线执行。除此之外零耦合，文档、skill、设计、角色矩阵全部分开。

---

## 1. 协同编码管线（留 Multi-Agent）

### 资产清单（现状位置 → 归属）

| 资产 | 现状位置 | 归属 |
|---|---|---|
| multi-model-orchestration SKILL（T1/T2/T3 路由 + 门禁 + 评审编排） | `Multi-Agent/skills/software-development/` | ✅ 保留 |
| provider-model-matrix（模型/API 实测矩阵） | 同上 references/ | ✅ 保留 |
| hermes-model-management / prisma-sqlite-patterns / apk-reverse-engineering / cli-anything-hermes | `Multi-Agent/skills/` | ✅ 保留（通用开发） |
| 视觉官位（vision_analyze = Qwen3.8-Max custom provider） | Hermes 全局配置 | ✅ 保留（跨项目服务，属编码管线视觉职责） |
| **qwen_coding_arch.png**（Qwen 接入编码管线架构图） | ⚠️ 误放在 `projects/mcm-2026/` | → 迁回编码侧文档 |
| qwen_vision_four_reviewer_arch.png（视觉/四评图） | ⚠️ 同上 | → 拆分：视觉部分留编码侧，四评部分随数模 |

### 角色矩阵（as-is，2026-08-14）

| 角色 | 模型 |
|---|---|
| 编排 / 任务分级路由 / 失败接管 | DeepSeek V4 Pro |
| T1 快速修复（<30min）/ T2 标准模块（0.5–2h） | kimi-coder (K2.7) |
| T3 复杂/长时程（>2h） | qwen-coder (Qwen3.8-Max) |
| 架构评审 | GLM 5.2 |
| 推理审查（低频） | Kimi K3 |
| 视觉 / UI / OCR / 渲染检查 / 页面验收 | Qwen3.8-Max 视觉官 |

### 待办设计（明天，范围已确认）

- **视觉迁移固化**：UI/视觉检查/OCR 全交千问，K3 收缩为推理审查位
- 视觉单点防护（生产者=检查者的共模风险：OCR 双读取头 / 程序化断言 / 种子图回归）
- 产出：编码管线专属设计文档 + 架构图

---

## 2. 数模管线（迁移新 MCM 仓库）

### 资产清单（现状位置 → 迁移去向）

| 资产 | 现状位置 | 迁移 |
|---|---|---|
| 1start-mathmodel / 2analysis-modeling / 3coding-visual / 4drawio / 5writing / 6verity（6 阶段流水线） | `Multi-Agent/skills/data-science/` | → MCM 仓库 |
| math-brainstorm / brute-force-think（脑暴/暴力求解） | 同上 | → MCM |
| mathmodel-v2-pipeline / mathmodel-pipeline-v3 / mathmodel-judge-perspective | 同上 | → MCM |
| mathmodel-figure-templates / typst-author / doctor | 同上 | → MCM（论文写作相关） |
| multi-agent-pipeline（6 阶段编排 + architecture-landscape.md） | `Multi-Agent/skills/` | → MCM；⚠️ architecture-landscape.md 内角色矩阵跨两管线，拆分时编码侧矩阵迁回 Multi-Agent |
| apk-forensics | `Multi-Agent/skills/data-science/` | 留 Multi-Agent（网安个人兴趣，非数模） |
| docs/mcm-2026/（V5 设计、judge v25/v26、v5_run 代码与首战产物、DWTS PDF） | `Multi-Agent/docs/` | → MCM |
| 设计文档库（V5_pipeline_design / judge_skill_v25/v26 / qwen 图） | `~/projects/mcm-2026/` | → MCM 仓库 docs（本地目录或废弃，以迁移为准） |
| mathmodel-agent-research/（生态调研库） | `~/projects/` | → MCM |
| 论文集（437 篇 PDF 语料） | `~/projects/2025年美大学生数学建模…/` | 数据仓库，不迁移（路径引用保留） |

### 角色矩阵（as-is，2026-08-14）

| 角色 | 模型 |
|---|---|
| 建模手 ×3（Stage 2 商议） | DeepSeek / GLM 5.2 / Kimi K3 |
| 检测层抽取 ×3（作者回避） | DeepSeek / GLM / Kimi |
| Stage 4 评审 ×3（相对排序） | DeepSeek / GLM / Kimi |
| 评委终评 v2.6 三评（零撰写上下文 + 扣分制 + 分位映射） | GLM / Kimi / DeepSeek |
| 视觉核查（渲染检查/图内文字提取） | Qwen3.8-Max（K3 视觉已退役） |
| 编码执行 | → 协同编码管线（T 路由） |

### 待办设计（明天，单独一份）

- **四模型化**：Qwen 成为第四全权模型（建模手/检测/Stage4/评委），证据类立即、打分类走校准阶梯
- 配套：同源偏移检测、阶梯 v2（有效轮次/版本锁/日历上限）、仲裁预算
- 产出：数模管线专属设计文档 + 架构图

---

## 3. 今天产物的处理

`projects/mcm-2026/pipeline_4model_design.md` + `pipeline_4model_arch.png/.html`（今天的混合设计）：
- **不删除，作存档**
- 明天按本文件 §1/§2 的待办范围**拆成两份独立设计重做**（编码管线一份、数模一份），各自出图

---

## 4. 仓库迁移执行清单（明天）

1. 用户新建 MCM GitHub 仓库（用户自己建）
2. `git mv` 迁移 §2 全部资产到 MCM 仓库（保留 git 历史）
3. Multi-Agent 仓库清理：删除已迁移目录；architecture-landscape.md 拆出的编码侧矩阵合并回 provider-model-matrix.md
4. 交叉引用更新：skill 内互相引用的路径、SOUL/编排提示词中的仓库路径
5. 推送验证：SSH 推流 + GitHub API 复核（既有流程）
6. 迁移完成后，两个仓库各自独立演进，本文件归档至 MCM 仓库 docs/
