# Multi-agent Mathematical Modeling（数模管线）

MCM / 数模竞赛的多智能体解题管线独立仓库。2026-08-15 起与**协同编码管线**（[xtr0928/Multi-Agent](https://github.com/xtr0928/Multi-Agent)）分仓库演进，本仓库承载数模专属的 skills、设计文档与实战产物。

## 仓库结构

```
skills/
  data-science/
    1start-mathmodel … 6verity/     # 6 阶段论文流水线（审题→建模→编码→图→写作→验收）
    math-brainstorm/                # 思路脑暴
    brute-force-think/              # 暴力求解
    mathmodel-v2-pipeline/          # 融合架构 v2.2（模式选择/建模辩论/门禁/评审团）
    mathmodel-pipeline-v3/          # 管线 v3.0 全题型执行手册（六路线判别/铁律/门禁）
    mathmodel-judge-perspective/    # 评委视角 skill v2.6（扣分记录制/四组14项机制）
    mathmodel-figure-templates/     # 图表模板
    typst-author/ · doctor/         # 论文写作支持
  multi-agent-pipeline/             # 6 阶段编排 + 架构全景
docs/
  V5_pipeline_design.md             # V5 管线设计（三 Agent 商议/claims registry/双轨迹/72h）
  judge_skill_v2{5,6}_design.md     # 评委 skill v2.5/v2.6 设计文档
  pipeline_4model_design.md         # 四模型化设计（存档，待拆分重做）
  2026_MCM-ICM_Problems/            # 2026 官方题目包
  DWTS_2026C_v5.pdf                 # 2026 C 题首战论文（15 页 LaTeX）
  v5_run/                           # V5 管线首战代码与全部运行产物
```

## 版本时间线（git tag）

| tag | 内容 |
|---|---|
| `v2.2` | 融合架构 v2.2（mathmodel-v2-pipeline 初版） |
| `pipeline-v2.3` `pipeline-v2.4` | 管线 v2.3/v2.4（C 题 O 奖精读驱动迭代） |
| `pipeline-v3.0` `pipeline-v3.1` | 全题型版（437 篇精读 → 4 条 100% 铁律 + 8 条高票规则；55 题批测） |
| `v5-pipeline` | V5 管线全链路并入（商议引擎/claims registry/双轨迹/首战产物） |
| `judge-v1.0` … `judge-v1.6` | 评委 skill 依据审计时代（官方 Triage 指南 → 84 篇 C 题精读） |
| `judge-v2.0` `judge-v2.1` | 437 篇全题型校准（HARD FAIL 扩 10 项） |
| `judge-v2.3` | 两段式评审（确定性审计前置） |
| `judge-v2.5` `judge-v2.5.1` | 六阶段架构 + 视觉评审层（三评仲裁/冷启动五层参照系） |
| `judge-v2.6` | 终版：四方数字 diff + 名实审查 + 扣分记录制评分引擎 |

## 模型角色矩阵（as-is）

| 角色 | 模型 |
|---|---|
| 建模手 ×3（Stage 2 商议） | DeepSeek V4 Pro / GLM 5.2 / Kimi K3 |
| 检测层抽取 ×3（作者回避） | DeepSeek / GLM / Kimi |
| Stage 4 评审 ×3（相对排序） | DeepSeek / GLM / Kimi |
| 评委终评 v2.6 三评（零撰写上下文） | GLM / Kimi / DeepSeek |
| 视觉核查（渲染检查/图内文字提取） | Qwen3.8-Max（K3 视觉已退役） |
| 编码执行 | → 协同编码管线（T1/T2/T3 路由，见 Multi-Agent 仓库） |

## 与协同编码管线的边界

- 本仓库**不依赖**任何编码管线 skill；Stage 3 的编码需求作为任务派发给协同编码管线执行。
- 铁律（两仓库通用）：写评分离、确定性门禁不认模型、72h 竞赛时间窗、评审零撰写上下文实例隔离、旧进程不杀并行对照。
- 分家说明：`docs/pipelines-split-2026-08.md`。
