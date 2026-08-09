---
name: mathmodel-v2-pipeline
description: >
  数模竞赛全流程 v2.2 融合架构——吸收 12+ 开源数模 Agent 项目与泛竞赛/科研 Agent
  经验后的理想编排：模式选择(全自动/人工把关) → 六维选题 → 三线并行解析 →
  建模辩论(三建模手+假设官) → 编码求解(反思循环) → 内部基准反馈(环形回环) →
  数值验证+证据+诚信三连门禁 → 全局写作 → 五人评审+格式门禁 → 排版交付。
  输出可提交论文(DOCX/PDF)。Use when solving any math modeling contest
  (MCM/ICM, CUMCM, 五一赛, 华数杯) end-to-end, 或用户说"用 v2 架构/全流程解题/
  自动写论文/暴力解题"。
triggers:
  - "v2架构"
  - "全流程解题"
  - "暴力解题"
  - "数模全流程"
  - "自动写数模论文"
  - "mathmodel v2"
---

# MathModel v2 Pipeline — 数模竞赛全流程融合架构

> 版本 v2.2 · 融合自：MathModelAgent / MathModel-Skill / xuec699-math-modeling-skills /
> J0Jng-MathModelingAgents / mathodology / make-no-mistakes / AlphaMath(AlphaProof) /
> agentic-kaggle / nvidia-kaggle / nature-paper-hub / DiscoveryWorld / 自有 OpenScore 体系

## 架构总览（10 阶段）

```
PHASE -1  模式选择    —— 开局第一问：全自动 or 人工把关？→ mode.json
PHASE 0   选题评估    —— 六维评分 + 一票否决 → input_manifest.json (SHA-256)
PHASE 1   问题解析    —— 题目结构化 / 问题分类 / 数据画像（并行）
PHASE 2   建模辩论    —— 建模手 A/B/C + 假设官 → 收敛门（差异<20%，≤3 轮）
PHASE 3   编码求解    —— 编码手(写→跑→修≤30轮) + 反思器 + 完成度检查器 + 基线对照
PHASE 3.5 内部基准反馈 —— 交叉验证评分 vs 基线 → 不达标回环 PHASE 2（≤2 轮）⟲
PHASE 4   证据链大纲  —— 🔢数值验证门禁 → 🔏证据门禁(SHA-256) → 🛡诚信门控(7类)
                       → 👁视觉审查(K3) → 大纲生成器
PHASE 5   论文写作    —— 论文手(全局) + 微单元扩写器 → final_paper_source.md
PHASE 6   评审门禁    —— 五人评审团(≥65 分) → 🔍格式门禁 → Rebuttal 修订(≤3 轮)
PHASE 7   排版交付    —— LaTeX→OMML 原生公式 + 三线表 → DOCX/PDF + 提交包 ZIP
```

## 模式选择（PHASE -1）—— 开赛第一问

开始任何工作前，**必须先问用户**：「全自动暴力解题，还是每个问题手动选择解法？」

| 模式 | 决策权 | 行为 | 适用 |
|------|--------|------|------|
| **Autopilot** | Agent | 三方案辩论自动收敛 → brute-force-think 多轮互评暴力迭代 → 全程无人介入直出论文 | 时间紧/题量大 |
| **Manual** | 用户 | 每个子问题关键决策点暂停，编号选项（Friendly Mode）让用户选模型路线/算法/求解器/图表方案，附「交给 AI，推荐」默认 | 想参与决策/追求可控 |

产出 `mode.json`，全流程所有决策点读取该文件。**Manual 模式允许中途切 Autopilot，反之亦可**（需用户确认）。

## Phase 0 · 选题评估

六维评估（各 1-5 分）：数学类型 / 数据可得性 / 算法复杂度 / 评价清晰度 / 写作难度 / 团队匹配度。
加权：`0.15/0.20/0.15/0.20/0.15/0.15`；**一票否决**：数据可得性=1 或团队匹配度=1。
产出：选题报告 + `input_manifest.json`（附件角色/字节数/**SHA-256**，固定本次运行输入快照）。

## Phase 1 · 问题解析（3 Agent 并行）

| Agent | 职责 | 产出 |
|-------|------|------|
| 题目结构化 | 拆 PDF/Word 题面为子问题 Q1-Qn，识别背景/约束/目标 | problem_analysis.json |
| 问题分类 | 从期望输出出发分类（评价/预测/优化/机理/分类/图论/统计/混合）→ 模型模板映射 | problem_taxonomy.json |
| 数据画像 | 字段类型/缺失率/清洗风险/样本量是否支撑模型复杂度 | data_profile.json |

## Phase 2 · 建模辩论

**建模手 A/B/C**（建议不同模型家族：GLM / DeepSeek / Kimi 各一）独立输出方案（只出思路+公式，不出代码）。
**假设官**：每个假设的完整生命周期——生成 → 论证必要性 → 主动挑战（放宽/移除会怎样）→ 敏感度实验计划。
**建模总监（收敛门）**：三方案交叉互评 → 差异排序 → 差异 <20% 收敛；不收敛最多 3 轮。
Autopilot 自动收敛；Manual 收敛后弹编号选项请用户确认。
产出：`model_route.json`（每问主模型/基线/备选/公式要求）+ `rubric_alignment.json`（评分点↔章节落点）。

## Phase 3 · 编码求解（Agentic 循环）

**编码手**：逐问生成 Python 代码，本地 Jupyter 沙箱真实执行；中文编码规范（双引号/禁 Unicode 转义/matplotlib 中文/图片语义化命名）；**每问强制先跑简单基线对照（均值/线性回归）**。
**反思器**：报错时结构化分析（语法/缺 import/变量类型/路径/其他）→ 修正版；反复失败切路径或简化，**禁止死循环**。
**完成度检查器**：每次执行后判定（数据步骤/文件保存/输出质量）→ 未完成继续，完成则总结。
产出：`run_manifest.json`（脚本/退出码/输入输出 SHA-256）+ `model_results.json` + `metrics.json` + `figure_index.json` + `table_index.json`。

## Phase 3.5 · 内部基准反馈（环形核心）

**基准评分器**：每问交叉验证分数 vs 基线差距评估。
- 主模型显著优于基线 → PASS 放行
- 不达标 → **回环 PHASE 2** 换模型路线或换算法（Autopilot 自动换 / Manual 弹选项），≤2 轮
产出：`baseline_report.json` + `iteration_log.json`（回环次数/决策记录）。

> ⚠️ 这是 v2 与旧版最大的区别：**流水线是环形不是线形**。结果质量驱动迭代，杜绝「一条道走到黑」。

## Phase 4 · 证据链四门禁 + 大纲

按顺序通过，任何一项不过即打回：

1. **🔢 数值验证门禁（确定性验证）**：随机采样代入验证公式等式成立 / 量纲与矩阵维度检查 / 边界条件行为检查 / sympy 符号化简比对——「可证性 > 概率性」，不靠 LLM 自查。未通过 → 公式打回重新推导。
2. **🔏 证据门禁**：重算 input/run manifest 的 SHA-256，输入/代码/结果任一变化旧报告全部作废；指标非空有限；无占位图表表格。
3. **🛡 诚信审查官（7 类阻断）**：引用真实性（DOI/CrossRef 验证）/ 数据真实性 / 模型正确性 / 统计有效性 / 结果一致性 / 逻辑完整性 / 表述规范性。通过条件：0 HARD FAIL + WARN ≤5，3 轮不过人工介入。
4. **👁 视觉审查官（Kimi K3）**：browser_vision 截图审查每张图表——数据标注清晰 / 图例重叠 / 坐标轴可读 / 与视觉规格一致。产出 `visual_review.json`。

**大纲生成器**：读全部证据链 JSON → 动态生成章节（5.x.1 建模思路 / 5.x.2 变量与推导 / 5.x.3 求解算法 / 5.x.4 结果分析 / 5.x.5 检验）；有证据图表写入 required_figures/tables。产出 `paper_outline.json` + `evidence_gate_report.json`。

## Phase 5 · 论文写作

**论文手（全局主笔）**：基于完整证据链整体写作 `final_paper_source.md`：
- 标题 `1 / 1.1 / 1.1.1` 编号；动态字数目标 `6500+1200Q`（摘要 800-1200 字）
- 图表先引用、后插入、再解释；公式先定义变量后解释；算法 Step 1/2/3
- 引文-参考文献双向闭环；禁止复制段落改数字凑篇幅
- 必须含模型评价/改进方向/推广/参考文献/附录代码说明
- 分节迭代：写→查证据→改

**微单元扩写器**：章节/段落/句级长文模板资产，辅助摘要/问题重述/假设/结果分析局部扩写。

## Phase 6 · 评审门禁

**五人评审团**（并行打分）：方法学评委 / 统计评委 / 领域评委 / **魔鬼代言人**（刻意挑刺）/ 主编 EIC。
Pass 标准：0 critical + ≤1 major + **总分 ≥65**；最多 3 轮；`review_verdict.json` 记录。
**Minor Revision** → 修订 Agent 逐条承接意见 → 送回重审。

**🔍 格式门禁**（确定性脚本 `check_paper_format.py`）：章节编号 / 字数下限 / 摘要关键词 / 图表引用闭环 / 占位符残留 / 引文闭环 / **OMML 公式数量** / PDF 渲染非空。产出 `format_check_report.json`。

## Phase 7 · 排版交付

**排版器**：Markdown → Word/PDF；LaTeX 公式经 latex2mathml + mathml2omml 转 **Word 原生可编辑 OMML**；三线表自动排版；字体/字号/行距按竞赛规范（黑体标题/宋体正文/Times New Roman 拉丁）。
**打包器**：提交包 ZIP = 论文 + 代码 + 数据 + CODE_MAP（代码与结果对应说明）。

## 契约 JSON 全清单（交接单）

```
input_manifest.json → problem_analysis.json → problem_taxonomy.json → data_profile.json
→ model_route.json → rubric_alignment.json → run_manifest.json → model_results.json
→ metrics.json → baseline_report.json → iteration_log.json → visual_review.json
→ evidence_gate_report.json → paper_outline.json → review_verdict.json → format_check_report.json
```

规则：相对路径 / 含 schema_version+generated_by+generated_at / 结果可追溯到 question_id /
下游使用前重算输入哈希，过期一律作废。

## 工程铁律（沿用 OpenScore）

- **30s 进度汇报**：每个阶段/Agent 派发后每 30 秒 poll 输出 ⏳/✅，禁止静默
- **超时降级**：GLM 30s 无输出 → 重启一次 → 再 30s → kill 切 Solo
- **熔断**：Agent 连续失败 3 次熔断；编码手 30 轮上限；评审/收敛/回环各有轮次上限
- **成本管控**：记录每阶段 token 消耗；超预算自动降级 LITE（跳评审团→单评委、诚信只跑 HARD FAIL）
- **断点恢复**：每阶段结束写 `workflow_memory.json`，中断后 `--status` 恢复，不丢上下文

## 与现有 skills 的关系

| 场景 | 调用 |
|------|------|
| 只需思路 | math-brainstorm（三模型脑暴） |
| 竞赛正式解题 | 本 skill（v2 全流程） |
| 已有 spec 纯编码 | multi-agent-pipeline（四阶段流水线） |
| 模型/密钥问题 | hermes-model-management 先查 |

## 配置要求（模型分配建议）

| 角色 | 模型 | 说明 |
|------|------|------|
| 编排/汇总 | DeepSeek V4 Pro | 主流程控制 |
| 建模手/分析 | GLM 5.2 / DeepSeek | 深度推理 |
| 编码手 | Kimi K2.7 | 代码生成 |
| 视觉审查 | Kimi K3 | browser_vision 截图 |
| 评审团 | GLM / DeepSeek | 严谨评分 |

## 参考

- 架构全景图：`portfolio/architecture.html`（v2.2 可视化，含全部泳道与回环）
- 来源调研：`projects/mathmodel-agent-research/`（12+ 项目源码/分析）
