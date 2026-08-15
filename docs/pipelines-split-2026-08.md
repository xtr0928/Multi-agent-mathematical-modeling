# 项目分家说明：数模管线 / 协同编码管线 / 通用工具（三仓库格局）

> 2026-08-14 初定两仓库 → 2026-08-15 用户最终定局：**三仓库**。
> 本文档是拆分执行的唯一依据，三仓库各存一份（Multi-Agent / MCM / Programming-Pipeline）。

---

## 0. 一句话分界

| | 协同编码管线 | 数模管线 | 通用工具 |
|---|---|---|---|
| 仓库 | **xtr0928/Multi-agent-programming-pipeline** | **xtr0928/Multi-agent-mathematical-modeling** | **xtr0928/Multi-Agent**（原地保留） |
| 是什么 | 通用编程执行管线：T1/T2/T3 路由 → 编码 → 门禁 → 评审 → 视觉/UI/OCR | MCM 竞赛解题管线：审题 → 商议建模 → 求解 → 成文 → 评审 | Hermes 多智能体体系的通用 skills 与编排（SOUL/README） |
| 依赖关系 | 不依赖数模 | Stage 3 编码需求 → 调用协同编码管线 | 宿主仓库，承载其余通用资产 |

**唯一耦合点**：数模 Stage 3 的编码需求 → 协同编码管线执行。除此之外零耦合。

---

## 1. 协同编码管线（Multi-agent-programming-pipeline）

### 资产清单（已迁移 2026-08-15）

| 资产 | 位置 |
|---|---|
| multi-model-orchestration SKILL（T1/T2/T3 路由 + 门禁 + 评审编排） | `skills/multi-model-orchestration/` |
| provider-model-matrix（模型/API 实测矩阵） | `skills/multi-model-orchestration/references/` |
| hermes-model-management（API key/连接验证，编排的配套 skill） | `skills/hermes-model-management/` |
| qwen_coding_arch.png（Qwen 接入编码管线架构图） | `docs/` |
| 视觉官位（vision_analyze = Qwen3.8-Max custom provider） | Hermes 全局配置（非仓库资产） |

### 角色矩阵（as-is）

| 角色 | 模型 |
|---|---|
| 编排 / 任务分级路由 / 失败接管 | DeepSeek V4 Pro |
| T1 快速修复（<30min）/ T2 标准模块（0.5–2h） | kimi-coder (K2.7) |
| T3 复杂/长时程（>2h） | qwen-coder (Qwen3.8-Max) |
| 架构评审 | GLM 5.2 |
| 推理审查（低频） | Kimi K3 |
| 视觉 / UI / OCR / 渲染检查 / 页面验收 | Qwen3.8-Max 视觉官 |

### 待办设计（范围已确认）

- **视觉迁移固化**：UI/视觉检查/OCR 全交千问，K3 收缩为推理审查位
- 视觉单点防护（生产者=检查者的共模风险：OCR 双读取头 / 程序化断言 / 种子图回归）
- 产出：编码管线专属设计文档 + 架构图

---

## 2. 数模管线（Multi-agent-mathematical-modeling，已迁移 2026-08-15）

- skills：6 阶段流水线（1start-mathmodel…6verity）、math-brainstorm、brute-force-think、mathmodel-v2-pipeline、mathmodel-pipeline-v3、mathmodel-judge-perspective、mathmodel-figure-templates、typst-author、doctor、_references、multi-agent-pipeline
- docs：V5 设计文档、评委 v2.5/v2.6 设计、四模型化设计存档、2026 题目包、首战论文与 v5_run 全部产物
- git tag 版本线：`v2.2` → `pipeline-v2.3/v2.4/v3.0/v3.1` → `v5-pipeline`；`judge-v1.0…v1.6/v2.0/v2.1/v2.3/v2.5/v2.5.1/v2.6`；`pipeline-4model-design`
- 角色矩阵：建模手×3（DS/GLM/K3）、检测×3、Stage4 评审×3、评委三评、视觉核查 Qwen、编码执行→协同编码管线
- 待办设计（单独一份）：四模型化（Qwen 第四全权模型，证据类立即/打分类走校准阶梯）

---

## 3. Multi-Agent 仓库（原地保留）

| 资产 | 说明 |
|---|---|
| skills/software-development/prisma-sqlite-patterns | 通用开发 |
| skills/software-development/apk-reverse-engineering | 网安个人兴趣 |
| skills/data-science/apk-forensics | 网安个人兴趣 |
| skills/cli-anything-hermes | 通用 |
| SOUL.md / README.md / .github | 体系编排与文档 |
| docs/pipelines-split-2026-08.md | 本文件 |

> 原 Multi-Agent 仓库中的数模与编码管线资产已按版本历史迁出（git filter-repo 保留提交历史）；历史提交仍保留在 Multi-Agent 的 git 历史中（未重写）。

---

## 4. 迁移执行记录（2026-08-15 已完成）

1. ✅ 数模仓库：git filter-repo 按 17 个路径过滤 + `docs/mcm-2026/ → docs/` 重命名，26 提交 + 20 个版本 tag 推送
2. ✅ 编码仓库：git filter-repo 按 2 个 skill 过滤 + 路径扁平化，5 提交 + 版本 tag 推送
3. ✅ 本地设计文档（评委 v2.6 设计、四模型化设计存档、架构图）随数模仓库导入
4. ✅ 本文档三仓库各存一份
5. 遗留：Multi-Agent 仓库的已迁出目录暂保留（git 历史仍在，删除前用户确认）
