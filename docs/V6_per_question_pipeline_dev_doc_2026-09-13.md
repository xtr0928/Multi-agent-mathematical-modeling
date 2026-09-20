# V6 逐问推进管线 · 详细设计文档（DDD）

> 日期：2026-09-13 ｜ v6 修订 2026-09-19 ｜ 状态：**待确认**（确认后开工 M1）
> 依据：2026-09-13 讨论拍板（逐问推进 / 上下文公理 / 重开实例 / git+哈希双保险（全系统 SHA-256） / 开场点将（先问后验） / 文件管理 / 同池评审+评审长 / 融合重写 / 自动回改）
> 前身：v5.2.1（本文档取代其"S0 一次参谋 + 一次拍板"全局编排；确定性地基全部继承）
> 流程图：`docs/V6_flowchart.html`（PNG 同名同目录）
> 阅读对象：实施者——M1 起照本文档开工

---

## 0. 术语表

| 术语 | 含义 |
|---|---|
| run | 一次完整解题过程；= 一个目录 = 一个 git 仓库 |
| 问（q） | 题面官方编号的最细粒度问题（Q1..QN，子问嵌套取最细编号） |
| 交接包 handoff | 实例唯一合法上下文：题面Qn + 数据索引 + 前一问冻结统一方案 + 全局口径表 + 已冻结产物 |
| 候选 candidate | 推理池某模型对本问的一份独立方案（`c01.md`…，匿名） |
| 统一方案 | 主模型融合重写产出的本问唯一执行依据（`unified_plan.md`） |
| D 决策 | 统一过程中逐处裁决的记录（采纳/否决/理由/影响面） |
| 池（Pool） | 本 run 开始时博士问询指定、并经可用性核查通过的模型集合：推理池 N / 评审池 R / 主模型 |
| 实例 | 一次 LLM 调用 = 一个全新实例（无历史、单发单收） |
| 冻结 | git commit（对象格式 sha256）+ MANIFEST.sha256.json + 版本 tag；冻结后只读 |
| 哈希口径 | **全系统统一 SHA-256**——内容级哈希（文件／参数／payload／清单条目）与 git 对象格式（sha256）同族，不再分层；v5 engine/hashing.py 现为 SHA-512，随 M1 统一改到 SHA-256（旧产物不进 v6 校验链） |
| 回改 | 冻结件被推翻 → 作废重算链 → 重新冻结（自动） |
| 数字身份证 | registry 五元组（value+script/input/params/env 哈希）绑定的可溯源数字 |
| 门禁 | 0 LLM 确定性检查；fail 即阻断（见 §6 八项） |
| 评审长 | 主模型**额外新实例**：汇总评审+证据 → 修订单/判定；不进原始评审票 |
| 半自动暂停 | orchestrator 在约定节点停下等博士裁决（文件握手协议，见 §2.5） |
| scratch / exports | run 内废料区（不进 git）/ 交付出口 |

---

## 1. 目标与非目标

### 1.1 设计目标（验收导向）

| # | 目标 | 验收判据 |
|---|---|---|
| G1 | 上下文零残留 | audit/calls.jsonl 每次调用可查；payload 原文落盘；任何实例无多轮 |
| G2 | 每问一个责任人一份冻结版 | 每问 FREEZE.json + git tag 齐全；下一问交接包哈希可复核 |
| G3 | 交付物零硬伤 | 八门禁（§6）全过才放行；反例数据集 100% 拦截 |
| G4 | 每数字可溯源 | 论文数字逐一命中 registry（否则阻断） |
| G5 | 修复不可自证 | 修复报告由脚本从断言生成；前后哈希留痕 |
| G6 | 可复现可断点 | 任意断点 resume；同输入重跑产物哈希一致 |
| G7 | 单目录自包含 | run 目录即归档单元；无文件外溢（含 Temp） |

### 1.2 非目标（边界）

- 不改 engine/gate 既有语义（只挂载调用）
- 不引入 LangGraph / DVC / 外部编排框架
- 不自动提交竞赛平台（交付永远人工确认）
- 不自创评分体系（评审语义沿用 judge skill v2.9）

---

## 2. 总体架构

### 2.1 主链（详见流程图）

```
S0 整题解析 → 逐问循环 q=1..N［P1 交接包 → P2 独立推理 → P3 分歧 → P4 主模型统一
→ P5 求解 → P6 门禁 → P7 评审+评审长 → P8 修复回路 → P9 冻结］
→ S_end 终局：跨问门禁 → 总评审 → 排版 → 检测层 → 交付门禁 → 交付冻结
```

### 2.2 铁律 R1–R8

| # | 铁律 | 说明 |
|---|---|---|
| R1 | 上下文公理 | 任何角色的任何一次调用 = 全新实例（建模手每一次思考、分歧记录、统一、评审、修复、重试，一视同仁）；单发单收、禁止多轮会话；上下文只含本问交接包；每次调用完整 prompt+payload 落盘并记哈希 |
| R2 | 逐问锁定 | 问内不跳步；问间只通过冻结版传递；版本号化（v1、v2…），禁止原地覆盖 |
| R3 | 统一=融合重写 | 主模型逐处裁决分歧；D 决策记录（采纳/否决/理由/影响面）；防"缝合怪" |
| R4 | 回改走作废重算 | 冻结件被推翻 → 传递闭包 stale → 拓扑序重算 → 重新冻结；自动，无需确认 |
| R5 | 开场点将（先问后验） | 每次开始建模先问博士（用几个/哪些模型：推理池/评审池/主模型）→ 问完只对所选别名做真调用可用性核查 → 状态表交博士处置 → 通过后冻结进 RUN.json |
| R6 | 花钱纪律 | 开跑前精确预估并获批准；运行中实时计数，超批准值硬停；池变更必须 commit |
| R7 | 交付物门禁 | 每问冻结前过本问门禁；终局过跨问一致性门禁（§6） |
| R8 | 双保险 | 每 run 独立 git 仓库（sha256 对象格式）；全量入 git；冻结点提交；MANIFEST.sha256.json 侧车——全系统哈希统一 SHA-256 |

### 2.3 角色矩阵

| 角色 | 实例数 | 模型 | 上下文 | 产出 |
|---|---|---|---|---|
| 题面解析 | 1 | 主模型 | 题面+附件 | problem_profile / 问题清单 |
| 候选推理 | N | 推理池 | 交接包 | candidates/*（匿名） |
| 分歧记录员 | 1 | 可配置（默认推理池之一） | 候选（匿名） | divergence.md |
| 假设官 | 1 | 可配置（默认推理池之一） | 候选＋分歧 | assumptions.md |
| Devil's Advocate | 1 | 可配置（默认推理池之一） | 候选＋分歧 | da_report.md |
| 统一者 | 1 | 主模型 | 候选+分歧+口径表 | unified_plan + decisions |
| 评审员 | R | 评审池 | 统一方案+产物+证据 | reviews/r{n}.* |
| 评审长 | 1 | **主模型额外新实例** | 评审票+证据 | repair_order + verdict |
| 修复者 | 0–K | 可配置（默认主模型新实例） | 修订单+产物 | repair/* |

**实例隔离**：统一者 / 评审长 / 下一问统一者 = 三个不同实例，严格分离；所有实例一律重开（R1）。

### 2.4 run 状态机与阶段标识

**阶段标识**（用于 state、audit、断点）：`S0`、`Q{q}/P{1..9}`、`END/{gate,review,layout,detect,build,export}`。

**状态流转**：

```
INIT → S0 → Q1/P1..P9 → Q2/P1..P9 → … → QN/P9 → END → DELIVERED
                ↑ 回改可回跳任意 Qk/P4（新版本，§3.11）
```

- 唯一事实源 = `state.json` + `change_log.jsonl`（append-only，扩展自 v5 ProgressStateMachine，见 §3.10）
- 恢复只信任哈希匹配的产物（v5 A13 语义保留）

### 2.5 半自动暂停协议（semi 模式，默认）

**暂停点**：① P4 完成后（统一方案过目）；② 每问 P9 冻结前；③ 争议升级（修复超 K 轮 / 评审长判 REDO / 主模型失效）。

**握手协议（文件式，`run_v6.py` 与博士解耦）**：

1. orchestrator 到达暂停点 → 写 `Qq/PAUSE_REQUEST.json`：
   ```json
   {"point":"after_P4","summary_md":"Q2/PAUSE_BRIEF.md",
    "options":["approve","edit","regenerate","abort"],"created":  "...ts..."}
   ```
   并打印显眼提示 + 摘要（PAUSE_BRIEF.md 含关键结论/分歧裁决摘要）
2. 博士操作：
   - 放行：`run_v6.py resolve --q Q2 --action approve [--note "..."]`
   - 修改：直接编辑 `Q2/unified_plan.md` 后 `resolve --action edit`（orchestrator 重算哈希，把人工修改记入 decisions 附录 MANUAL-n 条目）
   - 退回：`--action regenerate`（回 P2/P4 重推）
   - 中止：`--action abort`
   - 也可直接手写 `PAUSE_RESOLVE.json`（文件式等价）
3. orchestrator 轮询（5s）等待 resolve；`--auto-continue-after <s>` 可配置超时自动放行（默认：无限等待）
4. resolve 全量记入 change_log + audit

auto 模式：不暂停，仅记录与通知。

---

## 3. 模块详细设计

### 3.1 模块总览与代码落位

新增代码全部落 `pipeline/v6/`（入口 `pipeline/run_v6.py`）：

| 模块 | 文件 | 职责 | 规模估 |
|---|---|---|---|
| CLI 主驱动 | v6/cli.py + run_v6.py | 子命令、RunContext 装配、主循环 | ~450 行 |
| 点将与核查 | v6/probe_select.py | 点将问询、所选别名可用性核查（先问后验）、RUN.json 落盘 | ~150 行 |
| 调用审计层 | v6/calls.py | `call()` 封装：审计 journal + payload 落盘 + 重试语义 | ~150 行 |
| 交接包 | v6/handoff.py | 装配 + 校验（哈希/fresh/路径） | ~180 行 |
| 阶段驱动 | v6/stages.py | S0 / P2 扇出 / P3 / P4 / P7 / P8 编排 | ~500 行 |
| 提示词 | v6/prompts.py | 各角色 v6 系统提示（候选/分歧/统一/评审/评审长/修复） | ~300 行 |
| 求解执行 | v6/executor.py | 脚本快照、本机/服务器执行、产物回传核验、registry 登记 | ~350 行 |
| 冻结构建 | v6/freeze.py | git(对象格式 sha256) init/commit/tag + MANIFEST.sha256.json + FREEZE.json | ~200 行 |
| 门禁套件 | v6/gates/*.py | 八项门禁（§6） | ~1100 行 |
| 回改引擎 | v6/rollback.py | 影响闭包计算 + 重跑计划 + 自动执行 | ~250 行 |
| 状态机扩展 | v6/state.py（包 v5） | 阶段级 checkpoint / resume / 暂停等待 | ~200 行 |
| 预算计算 | v6/budget.py | 调用数公式 + 实时计数 + 硬停 | ~100 行 |
| 导出器 | v6/exporter.py | exports/ + EXPORT.json + 打包 + 外发核验 | ~200 行 |
| 测试 | tests/test_v6_*.py | 单测 + dry-run 集成 + 门禁回归 | ~1000 行 |

**复用（原样/改造）**：`engine/`（hashing·dag·registry·invalidation；hashing 算法随 M1 统一 SHA-256）、`gate/numeric_gate.py`（四断言+可复现性+build 钩子）、`gate/design_fidelity_gate.py`（P4→P5“方案-实现比对”= 其 S2.5 语义天然适用）、`layout/layout_gate.py`、`assumptions/`、`reflect/`、`seed/`、`bench/`、`visual/`、`cpp/executor.py`、`state/state_machine.py`、`llm_bridge.py`（生产调用桥）。**调用层唯一真实通道** = 兄弟仓库 `Multi-agent-programming-pipeline/pipeline/llm_client.py` 的 `ask()`（deepseek/dsflash/glm/kimi/qwen）；**`models.json` 为 M1 新建**的别名层（别名→provider/模型映射，含 gpt56sol 等待核验别名）。

### 3.2 CLI 详细设计

```
python run_v6.py plan    --topic <题包目录> [--pool pool.json]      # ① 点将问询（先问博士）→ ② 所选别名可用性核查 → ③ S0 解析 + 预算清单（先报后批）
python run_v6.py probe   --aliases <a,b,…> [--config models.json]   # 按需重探单个别名（默认被 plan 内联，日常不单跑）
python run_v6.py start   --approve <n> [--mode semi|auto] [--dry-run]
python run_v6.py status  [--q Q2]                                   # 进度/当前阶段/预算消耗
python run_v6.py resume                                             # 断点续跑（重放日志→dirty→继续）
python run_v6.py resolve --q Q2 --action approve|edit|regenerate|abort [--note ...]
python run_v6.py verify  [--gate all|Q2]                            # 门禁手动重跑
python run_v6.py freeze  --q Q2                                     # 手动冻结（补冻）
python run_v6.py export  [--out <外发目录>]                          # 生成交付件 + EXPORT.json（+复制核验）
python run_v6.py report  [--html]                                   # run 报告（进度/成本/门禁/评审汇总）
```

- 退出码：0 正常 / 2 门禁阻断 / 3 预算硬停 / 4 暂停等待中 / 5 致命错误
- `plan` 点将问询支持交互问答（stdin）与 `--pool pool.json` 预答文件两种等价形态（后者用于非交互/无人值守）
- `start` 校验：`--approve` 值 ≥ plan 基准值，否则拒绝开跑；运行中实时计数，**超过批准值硬停**（R6 的机械实现）
- `--dry-run`：全链用 DryRun 客户端（0 API），跑通目录/状态/冻结/门禁

### 3.3 点将与可用性核查（R5：先问后验）

**① 先问（点将问询）**——每次开始建模（新建 run）的起点，不预设清单、先向博士问：
- 推理池：用几个模型？（N≥2）＋ 指定别名（可“用默认建议池”一键作答）
- 评审池：用几家？（R≥3 建议）＋ 指定别名
- 主模型：是谁？（默认建议 gpt56sol；以核查结果为准）
- 两种等价形态：交互问答（stdin 逐项提问，每项带默认值，回车即默认）／`--pool pool.json` 预答文件（非交互、无人值守必须用后者）——产出同一份“点将草案”
- 当场约束预校验（不合规即回问）：main ∉ reviewers（评审长与评审分离语义）、N≥2、R≥3 建议

**② 后验（可用性核查）**——问询结束后，**只对草案里的别名**逐个核查（不再全量探测无关别名）：
- key 装载检查 → `list_models` → **真调用 smoke**（“请只回复两个字：可用”，max_tokens=64，timeout=90）
- 记录：`{alias, provider, model, key_ok, models_api_ok, smoke_ok, elapsed, error, models[]}`
- 输出 `probe.json`（落 run，见 §5.1）+ 打印状态表（含 403/额度/超时/思考档异常注记）
- 核查结果按别名缓存：博士改选后只补查新增/替换的别名，已核查别名不重复真调用

**③ 裁决（处置不可用项）**：
- 必需位全过（main ＋ 全部 N ＋ 全部 R ∈ smoke_ok）→ 写 RUN.json（池＋预算）并 commit → 进入 `start`
- 存在不可用别名 → 状态表＋原因交博士：改选（只补问缺位）／授权以可用候选补齐缺位（补齐后重新报批）／中止

**④ 中途失效政策**（不变）：单 alias 重试 2 次仍失败 → 标记 `degraded`，从池中移除 + 记 change_log + commit + 通知；**主模型失效 = 硬暂停**等博士（不静默换，R6）

### 3.4 调用审计层 calls.py（R1 的机械实现）

```python
def call(stage, alias, role, system, user, *, max_tokens=..., timeout=..., retries=2) -> dict
```

1. 组装 payload（system+user），计算 `payload_sha256`；写 `audit/payloads/<stage>__<alias>__<sha8>.txt`（原文）
2. 调 `llm_client.ask()`（经 `llm_bridge` 加载；流式、无代理、空响应重试——沿用 v5 实测修正）
3. 追加一行 `audit/calls.jsonl`（加锁，多线程安全）：
   `{ts, stage, alias, role, instance:"fresh", payload_sha256, payload_path, elapsed_s, usage, reasoning_chars, truncated, retries_used, outcome}`
4. **单发单收保证**：本封装无任何会话状态——每次调用物理上就是新请求（"重开实例"天然成立，重试=同 payload 新请求）
5. `truncated（finish_reason=length）`：视为失败，重试 1 次并记录（max_tokens ×1.5）
6. 失败语义：返回 `{error}`，由调用方决定（候选缺员/中止/降级）

### 3.5 交接包装配器（P1）

**步骤**：
1. 读 state，确认进入 `Qq/P1`
2. 汇总字段：题面 Qn 文本（S0 已切好）、data_index（逐项重新实算 SHA-256）、prev_unified（Qq-1 的 FREEZE 引用）、global_spec（当前版本）、frozen_artifacts（前问 solve 产物中"被本问需要"的索引——由 P4 之外不需要全量，装配时列 citations 供 P4 裁决）
3. **校验（不过即阻断）**：
   - 每个引用的文件存在且实算 SHA-256 == 声明值
   - 每个 data/artifact 的 registry 状态 ∈ {fresh}（stale 一律拒绝）
   - prev_unified 与本问 q 的编号连续（防跳问）
4. 写 `Qq/handoff.json`（schema §4.3），自身 SHA-256 记入 audit
5. 半自动：无暂停点（纯装配）

### 3.6 阶段驱动（P2/P3/P4/P7 编排细节）

- **P2 扇出**：默认**并行**（线程池，max_workers=推理池大小；无状态调用天然安全）；`--serial` 可关。每个候选：calls.call → 写 `candidates/c0i.md`；`authors.json` 记录 `c0i → alias`（冻结前不向任何实例暴露）。成功数 <2 → 中止本问（升级博士）
- **P3（分歧＋假设审计：记录员/假设官/DA 三实例，全部重开）**：渲染全部候选（匿名化标题“候选甲/乙/…”）→ ① 记录员 → `divergence.md`（议题/各方立场/影响面三栏格式；空清单允许）；② 假设官 → `assumptions.md`（四步：登记/必要性/挑战/敏感度 + 隐式假设映射）；③ DA → `da_report.md`（反事实+实验设计挑战）。三者默认开（待确认②），可关
- **P4**：渲染候选（匿名）+divergence+assumptions+da_report+口径表 → 主模型实例 → `unified_plan.md`（模板 §4.5）+ `decisions.json`（§4.6）+ 全局口径表增量提案。产出缺章节/决策缺理由 → 重试 1 次 → 仍缺则升级
- **P7**：R 家评审（并行，fresh）→ `reviews/r{i}.json`（结构化，§4.9）；评审长（主模型新实例）→ `repair_order.json`（§4.10）+ `verdict ∈ {PASS, FIX, REDO, ESCALATE}`。verdict 规则：
  - 任一 blocking issue → FIX（进 P8）
  - ≥2 家 REDO 或评审长判"核心方向错误" → REDO/ESCALATE（semi 暂停问博士；auto 转回改评估）
  - 无 blocking 且无 REDO → PASS（可冻结）
- **P8**：对 repair_order 逐项：确定性项 = 脚本修复 + 断言；文本项 = 修复实例（fresh）→ 修改后**强制重过 P6** + 重评（全量轻扫，评审长逐项确认 fixed）；≤K 轮（默认 2），超限 ESCALATE

### 3.7 求解执行器

- 脚本快照：执行前把求解脚本复制到 `Qq/solve/scripts/`（连同 SHA-256）——registry script_hash 的可复现依据
- 双通道：本机 subprocess / 服务器 SSH（沿用 C 题模式）；服务器回传必须附清单 → 逐文件 SHA-256 核验 → 落 `Qq/solve/remote/<stamp>/`
- 产物登记：registry 五元组写入 `Qq/solve/registry_export.json` + 主 registry.db
- 可复现性断言：同输入重跑 3 次哈希全等（复用 numeric_gate 的可复现性断言）

### 3.8 门禁套件

见 §6（独立章节，含算法与正反用例）。

### 3.9 冻结构建器 freeze.py

1. `git init --object-format=sha256`（run 创建时）
2. 冻结序列：收集本问产物清单 → 逐个实算 SHA-256 → 写 `FREEZE.json`（§4.11）→ 更新 `MANIFEST.sha256.json`（§4.12）→ `git add -A` → `git commit -m "<模板>"` → `git tag freeze/Qq-v<n>` → checkpoint
3. 提交信息模板：`Q1 freeze v1 ｜ 门禁 pass ｜ 产物 23 ｜ D决策 5`
4. 取回旧版本：`git show freeze/Q1-v1:Q1/unified_plan.md`
5. 完整性自检：`git fsck` + tag 列表 + MANIFEST 抽检（verify 子命令）
6. **双源裁决与派生核验**：提交后 `git ls-tree -r freeze/Qq-v<n>` 与 MANIFEST/FREEZE 逐条比对（不一致 = 失败重冻——把 git/MANIFEST 双源分歧在写入时消灭）；残留分歧裁决：run 仓库内**以 git 对象为准**（MANIFEST 降级为提示），导出包内**以 EXPORT.json 为准**

### 3.10 状态机与恢复（扩展 v5 ProgressStateMachine）

- 粒度：stage 级 checkpoint（`Qq/Pn` 每完成写一次）；`change_log.jsonl` append-only
- 恢复协议（`resume`）：重放日志 → 重建 dirty 全集 → 与磁盘实算哈希比对 → 输出恢复起点 → 从该 stage 继续；**完成标记一律不信，只信任哈希匹配的产物**
- 暂停等待态持久化：resume 时若存在未 resolve 的 PAUSE_REQUEST → 先恢复等待
- 时间窗（TimeWindowStateMachine）只读复用：writing 25% 硬保底 + 预授权降级清单保留

### 3.11 回改引擎 rollback.py（R4）

**触发**：P7 评审 / 终局总评审发现"前问冻结件"问题（或本问统一稿被推翻）。

**算法**：
1. 定位：问题归属问 k、归属产物集合 A（统一方案/求解产物/口径表）
2. 影响闭包：以 registry/DAG 计算 A 的传递闭包（stale 集）
3. 重跑计划 = 拓扑序：`Qk/P4(重写) → Qk/P5..P9`；下游问按 stale 影响度分级：受影响产物所在阶段重跑，未受影响环节仅刷新交接包 + 重过门禁
4. 执行：自动（semi 模式下先给博士一页《回改摘要》广播，但**不等待**——R4 自动执行；若博士要拦，用 `resolve --action abort` 窗口期内中止）
5. 版本：全部产出新版本号（v2…），旧版本靠 git tag 取回
6. 次数上限：全局 R_max=3；超限硬暂停升级博士

### 3.12 导出器 exporter.py

- `export` 生成 `exports/<竞赛>_<题号>_<日期>/`：论文 PDF + result 表 + 支撑材料 zip + 交付说明 + MANIFEST + 评审汇总
- `EXPORT.json`：文件清单 + 逐个 SHA-256 + 生成命令 + 来源 FREEZE 引用（可复现 + 可核验）
- 外发：`--out <目录>` 复制到博士指定目录（默认不复制）；复制后逐文件哈希核对并打印核对报告
- 归档打包：`<竞赛>_<题号>_<RUN_ID>.zip`（run 目录整包）

### 3.13 v5.2.1 → v6 映射总表

| v5.2.1 | v6 | 动作 |
|---|---|---|
| orchestrator.py（S0-S7 壳） | v6/cli.py + stages.py | 重写为主驱动（逐问循环） |
| estimate_calls() | v6/budget.py | 重写（公式 §8 + 硬停） |
| S1 参谋组整解 | P2 逐问候选 | 语义变更 |
| S1.5 单次拍板 | P4 每问统一 | 变更（N 次小拍板） |
| S2 双轨迹 | — | 删除（逐问内候选多样性替代） |
| S3 评审+投票 | P7 评审+评审长 | 强化（评审长新实例） |
| S4 数值门禁 | P6 + 终局门禁八项 | 扩展 |
| S5/S5b/排版检测层 | S_end 保留 | 原样 |
| S6 修复回路/S7 回归门 | P8 + 终局 | 并入 |
| engine/gates/state/… | 原样复用 | 挂载 |

---

## 4. 数据契约（完整 schema）

### 4.1 RUN.json

```json
{
  "run_id": "CUMCM2026_C_20260913",
  "competition": "CUMCM2026", "problem": "C",
  "created": "2026-09-13T21:00:00+08:00",
  "mode": "semi",
  "pool": {"main": "gpt56sol", "reasoners": ["deepseek","glm","kimi","qwen","gpt56sol","ds41flash"],
            "reviewers": ["deepseek","glm","kimi","qwen","gpt56sol","ds41flash"]},
  "budget": {"baseline_calls": 86, "approved_calls": 86, "reserve_cap": 108},
  "code_version": {"pipeline_commit": "<git sha256>", "models_json_sha256": "..."},
  "questions": ["Q1","Q2","Q3","Q4"],
  "delivery_target": null
}
```

### 4.2 state.json（摘要视图；事实源 = change_log）

```json
{"stage": "Q2/P4", "started": "...", "budget_used": 37,
 "questions": {"Q1": {"freeze_version": 1, "tag": "freeze/Q1-v1", "status": "frozen"},
               "Q2": {"status": "in_progress"}},
 "pause": {"pending": false}}
```

### 4.3 handoff.json（完整）

```json
{
  "run_id": "...", "question": "Q2", "assembled_at": "...",
  "problem_text": {"path": "S0/q2_text.md", "sha256": "..."},
  "data_index": [{"path": "inputs/附件1.xlsx", "sha256": "...", "registry": "fresh", "desc": "风电/光伏/负荷数据"}],
  "prev_unified": {"Q1": {"path": "Q1/unified_plan.md", "sha256": "...", "freeze": "freeze/Q1-v1", "version": 1}},
  "global_spec": {"path": "S0/global_spec_v1.md", "sha256": "..."},
  "frozen_artifacts": [{"path": "Q1/solve/tou_costs.json", "sha256": "...", "claim_ids": ["c_q1_cost_35012"]}],
  "instructions": "本问方案必须引用上述冻结数字，不得另起口径；引用即写 claim_id"
}
```
校验规则（§3.5）：哈希实算相等 / registry=fresh / 问编号连续 / 路径全部存在于 run 内（禁外链）。

### 4.4 authors.json（匿名映射，密封）

```json
{"c01":"glm","c02":"kimi","c03":"gpt56sol","c04":"deepseek","c05":"qwen","c06":"ds41flash",
 "sealed_until": "Q2/P9", "note": "冻结前不得向任何实例暴露映射"}
```

### 4.5 unified_plan.md 模板（必备章节）

```
§1 本问目标与题面条款逐条对照
§2 模型形式（公式，含符号定义）
§3 参数与取值来源（引用 handoff 的 data_index/claim_id）
§4 算法与实现要点（含伪代码或关键步骤）
§5 口径清单（单位/取整/时点/边界条件）
§6 预期产物清单（文件级：名/格式/行数或形状）
§7 验证点清单（供 P6 门禁逐条执行）
§8 D 决策索引（引用 decisions.json 的 id）
```

### 4.6 decisions.json

```json
{"decisions": [{
  "id": "Q2-D3", "issue": "预测信息集边界",
  "chosen": "仅用决策时点已发布预报",
  "adopted_from": "候选乙", "rejected": [{"from": "候选甲", "why": "使用了未发布预报，K≥2 场景违规"}],
  "impact": "费用影响约 5% 量级", "rollback_affects": ["Q2/solve/*", "Q3/unified_plan.md"],
  "manual": false }]}
```

### 4.7 global_spec.md 模板

符号表 / 单位约定 / 参数取值 / 结算与计费规则 / 时间基准 / 版本变更记录（每问统一者只许扩展或显式修订——修订必须列 D 决策）。

### 4.8 candidates 命名

`candidates/c01.md … cNN.md`；文件头固定三行：`# 候选 cNN`/`模型：<不写真实名>`/`生成：<ts> <stage>`；正文自由格式。

### 4.9 评审票（reviews/r{i}.json）

```json
{"reviewer": "glm", "round": 1, "question": "Q2", "verdict": "FIX",
 "scores": {"模型": [23, 30], "求解": [18, 25], "检验": [18, 25], "写作": [14, 20]},
 "issues": [{"id": "R1-1", "severity": "blocking", "target": "solve",
             "desc": "储电量列与充放电量不闭合", "evidence": "result3 首行 10645.175 ≠ 声明 6000"}]}
```
severity ∈ blocking/major/minor；scores 保留各家原始分母。评审长有权把 blocking 降级为 major，但必须书面理由。

### 4.10 repair_order.json

```json
{"question": "Q2", "round": 1, "verdict": "FIX",
 "items": [{"id": "F1", "from_issue": "R1-1", "target": "Q2/solve/result3.xlsx",
            "action": "按 η=0.9 重算储电量列并从真实窗口起点重出",
            "assertion": "首行储电量==声明S0 且 逐段滚推残差<1e-6",
            "status": "open"}]}
```
status ∈ open/fixed/waived（waived 必须评审长+博士双签）。

### 4.11 FREEZE.json

```json
{"question": "Q1", "version": 1, "tag": "freeze/Q1-v1", "git_commit": "sha256:...",
 "frozen_at": "...", "files": [{"path": "Q1/unified_plan.md", "sha256": "..."}],
 "gates": {"pass": true, "report": "Q1/gates/report.json"},
 "decisions_count": 5, "review_verdict": "PASS"}
```

### 4.12 MANIFEST.sha256.json（run 级）

```json
{"run_id": "...", "updated_at": "...", "entries": [
  {"path": "Q1/solve/tou_costs.json", "sha256": "...", "role": "solve_artifact",
   "freeze": "freeze/Q1-v1", "produced_by": "script:solve_q1.py", "params_hash": "..."}]}
```

### 4.13 calls.jsonl / payloads/

见 §3.4。payload 文件名：`<stage>__<alias>__<sha8>.txt`；JSONL 每行一条。

### 4.14 EXPORT.json

```json
{"export_id": "...", "created": "...", "source_freezes": ["freeze/Q4-v1"],
 "files": [{"path": "论文.pdf", "sha256": "..."}, {"path": "result1.xlsx", "sha256": "..."}],
 "commands": ["xelatex main.tex (×2)", "python gen_results_v6.py"],
 "manifest_ref": "MANIFEST.sha256.json"}
```

### 4.15 registry 数字身份证

沿用 v5 五元组（`value + script_hash + input_hash + params_hash + env_hash`）+ predicate 状态词；v6 增加：`claim.citations[]`（被子引用）与终局论文数字审计接口 `audit_paper_numbers()`。

---

## 5. 阶段逐步流程

### 5.1 S0（一次）

1. 建 run 目录（模板 §7）+ `git init --object-format=sha256` + 初始 commit（tag `run-start`）
2. **开场点将（先问后验，§3.3）**：点将问询（先问博士：用几个/哪些模型）→ 只对所选别名做可用性核查 → 状态表裁决 → `probe.json` 落 run、池冻结进 RUN.json
3. 题包拷入 `inputs/`，逐文件 SHA-256 登记 data_index
4. 主模型实例（重开）→ `problem_profile.md`（题面结构/问题编号与建议粒度/依赖初判/数据字典）
5. 脚本切分题面 → `S0/q{n}_text.md` 逐问文本（人工可核对）
6. 生成 `global_spec_v0.md`（模板 §4.7）
7. checkpoint + commit

### 5.2 每问循环（P1–P9）

| 阶段 | 步骤要点 | 失败处理 | 暂停点 |
|---|---|---|---|
| P1 | 装配 handoff → 校验（§3.5 四条）→ 落盘 | 校验不过 = 硬阻断 | — |
| P2 | 并行扇出 N 候选（§3.6）→ candidates/ + authors.json | <2 家成功 → 中止问 | — |
| P3 | 匿名渲染 → 记录员＋假设官＋DA（三实例）→ divergence.md＋assumptions.md＋da_report.md | 重试 1 次 | — |
| P4 | 主模型统一 → unified_plan + decisions + 口径增量 | 缺章节/缺理由 → 重试 1 次 | **① after_P4** |
| P5 | 脚本快照 → 执行（local/remote）→ 回传核验 → registry 登记 | 求解失败 → 修复回路/重试 | — |
| P6 | 每问四项门禁①②③⑤：提交表比对·数值恒等式·口径一致性·信息集合规 → gates/report.json | fail → P8 | — |
| P7 | R 家评审（并行）→ 评审长汇总 → repair_order + verdict | REDO → 升级 | **③ 争议升级** |
| P8 | 逐项修复 → 强制重过 P6 → 重评核对 | >K 轮 → 升级 | 争议升级 |
| P9 | FREEZE.json → MANIFEST → commit + tag → checkpoint | — | **② before_freeze** |

### 5.3 终局（S_end）

1. 跨问一致性门禁（④③全局版）
2. 全池总评审（+评审长）→ 若发现前问问题 → 回改（§3.11）
3. 排版（视觉官 + layout_gate + 官方模板清单检查 + 篇幅门禁）
4. 检测层（作者回避抽取，沿用 v5 S5b 语义）
5. 交付门禁（①②④⑦⑧ on final）+ LaTeX 编译（⑧）
6. exports 生成（§3.12）→ 交付冻结（tag `deliver-<date>`）→ 归档打包

---

## 6. 门禁详细设计（八项）

| # | 门禁 | 输入 | 算法要点 | 挂载 | 反例（必拦，来自 C 题真实数据） |
|---|---|---|---|---|---|
| ① | 提交表机械比对 | 官方模板 + 提交表 | sheet 名/表头/行列数/日期范围/口径标注逐格比对 | 每问 + 终局 | 缺列/错行数构造样本；官方模板本身 6 段/日（"48,096 行"类误判要有反证据能力） |
| ② | 数值恒等式 | 提交表 + 统一方案声明 | SOC 滚推=列值（η=0.9 逐段）；首行==声明初值；功率平衡残差（max/mean/超限行数） | 每问 | result2 日界恒 1,200（应 2,200）；result3 首行 10,645.175≠声明 6,000 |
| ③ | 口径一致性 | 论文 + 表 + 标注 | 每个数字声明覆盖区间；334/365 不混用；双口径绑定提交表 | 每问 + 终局 | 论文标 365 天而表 334 天；"双口径只有一套进表" |
| ④ | 跨文件数字一致性 | 论文 + 表 + registry | 论文每个数字 → registry 溯源；未命中即阻断 | 终局 | 18.92%（现存任何数字都复现不出） |
| ⑤ | 信息集合规 | 统一方案 + 数据发布时间 | 每个输入声明"可用时刻 vs 决策时刻"；未发布预报不得进决策 | 每问 | K≥2 使用未发布预报；"利用半价退费少报"类表述审查 |
| ⑥ | 修复闭环验证 | repair_order + 产物 | 每项修复对应机器断言，**修后实跑断言**+前后哈希；报告由脚本生成 | P8 | "修复声称偏差 0.000000，台账 Σ充放=-9,600 vs 末值差=-4,800" |
| ⑦ | 送审核验包 | 送审材料 + 证据库 | 每个主张附字节证据（表摘录/哈希/diff），自动组装 | 终局 | 第二轮"4/6 项无法核验" |
| ⑧ | 冻结构建+编译 | 源码 + 产物链 | 依赖序重建（表→论文→编译）+ LaTeX 必须编译通过 + 时序断言 + 哈希清单 | 终局 | "未编译 LaTeX = 未验证交付物"；18:16 表 vs 18:19 论文的"同源"3 分钟差 |

所有门禁：0 LLM、可独立脚本运行（挂 build 钩子）、输出 `gates/report.json`（finding 级：check/verdict/evidence）。

---

## 7. 文件管理与归档规范

**总原则：一个 run = 一个目录 = 一个 git 仓库。** 任何东西不落在 run 目录之外（含临时脚本，不再散落系统 Temp）。存放位置：`<代码仓库>/runs/<RUN_ID>/`，外层代码仓库 .gitignore 排除 `runs/`。机器路径全 ASCII，人读文档可用中文。

**目录树（固定模板，脚本自动创建，禁止手工新增顶层）**：

```
runs/<RUN_ID>/                    # 独立 git 仓库（object-format=sha256）
├── RUN.md / RUN.json / probe.json  # 人读 + 机读元数据（池子/预算/版本；probe.json = 开场可用性核查足迹）
├── MANIFEST.sha256.json          # 全冻结产物哈希侧车（哈希统一 SHA-256）
├── inputs/                       # 【只读】题面包（题面/附件/官方模板）
├── S0/                           # problem_profile · data_index · global_spec_v0 · q{n}_text.md
├── Q1/ ... QN/
│   ├── handoff.json              # 交接包（唯一合法上下文）
│   ├── candidates/ c01.md..cNN.md · authors.json
│   ├── divergence.md
│   ├── unified_plan.md · decisions.json
│   ├── solve/                    # scripts/(快照) + local/ + remote/(服务器往返) + registry_export.json
│   ├── gates/report.json
│   ├── reviews/r{i}.json · repair_order.json
│   ├── repair/
│   ├── PAUSE_REQUEST/RESOLVE.json  # 半自动按需（§2.5）
│   └── FREEZE.json
├── final/                        # 终局：门禁/总评/论文/排版/检测层/交付包
├── audit/                        # calls.jsonl · payloads/ · role_audit.json · registry.db
├── scratch/                      # 【不进 git】中间废料区：冻结时未登记文件默认清空
├── exports/                      # 交付出口：EXPORT.json + 分层交付件 + zip
└── state.json · change_log.jsonl # 唯一事实源（§3.10）
```

**写权限分层**

| 区域 | 谁能写 | 规则 |
|---|---|---|
| inputs/ | 无人 | 进入即锁定；新增=新登记，不得修改原件 |
| S0/ · Qq/ · final/ · audit/ | 对应阶段脚本 | 冻结后转只读；再改必须走回改协议（新版本+新 tag） |
| scratch/ | 任意 | 不进 git；冻结时未登记文件默认清空 |
| exports/ | 打包脚本 | 每次导出附 EXPORT.json |

**防垃圾三则**：① 顶层白名单（治 cumcmv9 的 13 顶层目录大杂烩）；② 不设"废弃/旧版"目录——旧版本 `git show freeze/Q1-v1:...` 取回；③ 临时脚本归位（solve/scripts/ 快照或 scratch/），禁止散落 Temp（上次 475 文件/268MB 遗留）。

**git 提交纪律**：只在冻结点提交（S0 后 / 每问冻结 / 修复前后 / 交付）；二进制全量入库（仅冻结点）；提交信息模板见 §3.9。

**归档与交付**：run 目录即归档单元；交付件 exports/ 生成；外发目录由博士指定并做哈希核对；支撑材料 zip 内附交付说明+MANIFEST+评审汇总。

---

## 8. 成本模型与预算流程

```
calls = 1(S0) + Σq [ N推理 + 1分歧 + 1统一 + 1假设官 + 1DA + R评审 + 1评审长 ] + 29(终局)
      = 1 + Σq (N + R + 5) + 29
终局 29 = 总评 6 + 评审长 1 + 排版 1 + 检测层 20 + 交付 1
```

| 示例 | N=6,R=3,4问 | N=6,R=6,4问 | N=4,R=3,4问 | N=6,R=3,3问 |
|---|---|---|---|---|
| 基准 | 86 | 98 | 78 | 72 |

- `plan` 输出（先问后验完成、池最终确定后现算）：基准 + 储备上限（基准×1.25，覆盖修复/回改）
- `start --approve <n>`：n ≥ 基准才可开跑；运行中实时计数（budget_used），**达到批准值硬停**（退出码 3）
- 修复/回改增量实时报告，突破储备上限 → 硬停等博士

---

## 9. 错误处理与运行策略

| 场景 | 处理 |
|---|---|
| LLM 超时/连接断 | 重试 2 次（同 payload 新请求，退避 2s×n）；仍失败 → 该实例 failed |
| 403/额度耗尽 | 不重试，标记 degraded + 通知；池移除 + commit；主模型失效=硬暂停 |
| 空响应/截断 | 空响应内层重试（v5 实测逻辑）；截断=失败重试 1 次（max_tokens×1.5，记录） |
| 候选不足（<2 家成功） | 中止本问 → 升级博士 |
| 门禁 fail | 进 P8 修复；同项连续 2 轮修不过 → 评审长判定 → 升级 |
| 评审争议（REDO/分歧大） | semi：暂停问博士；auto：回改评估 → 必要时 ESCALATE |
| 修复超 K 轮 | 硬暂停升级（附全部字节证据） |
| 回改超 R_max=3 | 硬暂停升级 |
| 暂停超时 | 默认无限等待；`--auto-continue-after` 可选自动放行 |
| 磁盘/服务器掉线 | 求解走本机降级通道；服务器回传核验不过=拒绝登记并重传 |
| 并行调用触发限流 | 自动降级为串行（逐家）+ 退避 |
| 进程被杀/断电 | `resume`：重放日志 → 哈希比对 → 从最近可信 stage 继续 |

---

## 10. 测试与验收计划

### 10.1 单元测试（新模块逐一）
handoff 校验四规则（含缺哈希/坏 fresh 反例）· MANIFEST/FREEZE 生成与抽检 · freeze tag 与取回 · 状态机 resume（断电注入）· 回改闭包计算 · 审计落盘（多线程）· budget 计数与硬停 · probe 表解析 · 导出核验。

### 10.2 dry-run 集成（M1 验收）
全链 DryRun：`plan --dry-run` → `start --dry-run`（4 问全跑）→ 断言：目录树完整 / 状态转移序列正确 / 每问 FREEZE+tag 存在 / calls.jsonl 条数==预算公式 / 重启 resume 一致。

### 10.3 门禁正反回归（M4 验收，反例 = C 题真实坏数据）
§6 表末列全部反例样本 + 正例（修复后版本）；**门禁对反例 100% 拦截、对正例 100% 放行**。

### 10.4 真彩排
- M2：单问真调用（小池），验证预算吻合、全链产物、审计完整、冻结可复核
- M3：公开题全流程（可以往年赛题），验证各问冻结链 + 终局门禁 + 可复现

### 10.5 验收 checklist
□ 零 API dry-run 全绿 □ git 完整性自检 □ 上下文审计可查 □ 门禁回归全过 □ 主模型/评审长实例隔离记录 □ 回改演练一次 □ 断点恢复演练一次 □ 操作手册可用

---

## 11. 实施计划（M1–M5）

| 里程碑 | 任务 | 产出 | 验收 |
|---|---|---|---|
| **M1 骨架**（0 API） | 目录模板+RunContext；state 扩展；calls 审计层；handoff 装配校验；阶段驱动 dry-run；freeze；CLI 十个子命令（probe/plan/start/status/resume/resolve/verify/freeze/export/report）；集成测试 | `pipeline/v6/*` 可跑；dry-run 全链 | 10.2 全过 |
| **M2 单问真彩排** | 真探测+点将；单问真调用全链 | 1 个真实问的完整冻结链 | 预算吻合 + 10.4 判据 |
| **M3 全流程彩排** | 公开题 4 问全跑（含 1 次回改演练） | 完整 run 目录 | 终局门禁过 + 可复现 |
| **M4 门禁回归** | 八门禁 + C 题坏数据回归集 | 门禁测试集 + 报告 | 反例 100% 拦 |
| **M5 实战就绪** | 操作手册（点将/暂停/应急/恢复）+ 赛前演练 | 手册 + 演练记录 | checklist 全过 |

---

## 12. 风险与开放问题

| # | 风险/问题 | 缓解 |
|---|---|---|
| 1 | 评审长=主模型汇总自家统一稿，自证风险 | 逐条回应评审发现；降级 blocking 需书面理由；争议升级博士；数值门禁独立 |
| 2 | 回改成本失控 | R_max=3 + 影响分级重跑 + 预算硬停 |
| 3 | 全量 git 体积 | 冻结点提交 + 定期 `git gc` + 单 run 独立仓库 |
| 4 | dry-run 与真实差异 | M2 尽早真彩排 |
| 5 | 并行限流 | 自动转串行 + 退避 |
| 6 | **待确认①**：评审长语义（默认：不进原始评审票） | 一句话可改 |
| 7 | **待确认②**：假设官/DA 每问默认开 | 一句话可改 |
| 8 | **待确认③**：暂停点选集（默认 ①P4后 ②冻结前 ③争议升级） | 一句话可改 |
| 9 | 先问模式依赖博士开场在场（auto/无人值守无人应答） | auto 模式必须以 `--pool pool.json` 预答文件替代问答；缺失则 `start` 拒绝开跑 |
| 10 | git 与 MANIFEST 双源分歧（崩在两写入之间／手改清单／导出包无 .git） | 冻结末尾派生核验（写入时消灭）+ 分场景裁决：repo 内 git 优先；导出包 EXPORT.json 优先 |

---

## 13. 附录

### A. 命名规范
- stage：`S0` / `Q{q}/P{n}` / `END/<gate|review|layout|detect|build|export>`
- tag：`run-start` / `freeze/Q{q}-v{n}` / `deliver-<yyyymmdd>`
- commit：`Q{q} freeze v{n} ｜ 门禁 pass ｜ 产物 n ｜ D决策 n`
- payload：`audit/payloads/<stage>__<alias>__<sha8>.txt`
- 哈希：全系统统一 SHA-256（清单字段名 `sha256`）；git commit id 记作 `sha256:<hex>`（对象格式，与内容哈希同族）

### B. 提示词要点（全文落 prompts.py）
- 候选：按 unified_plan 模板前置要求组织；必须给"验证点清单"；引用冻结数字须写 claim_id
- 分歧记录员：只列冲突点+立场+影响面，不做裁决
- 统一者：逐处裁决，D 决策必填理由与影响面；缺章节即废稿
- 评审：对照 §4.5 八章节 + 门禁报告逐条审；issue 必须带 evidence
- 评审长：汇总→修订单；降级 blocking 必须书面理由
- 修复：只修 repair_order 项，禁止顺带改动；产出修复说明（脚本生成）

### C. 与 v5 引擎对接点
- `ClaimRegistry`：register_input/script/params + WriteGuardError 语义照用
- `ProgressStateMachine.recover(current_hashes)`：v6 resume 直接调用
- `numeric_gate.NumericGate`：P6/终局可复现性断言复用
- `design_fidelity_gate.check_fidelity`：P4→P5 的"方案-实现比对"复用（impl_manifest 由执行器生成）
- 调用层：`llm_bridge.make_backend()` → 兄弟仓库 `llm_client.ask()`（五 provider：deepseek/dsflash/glm/kimi/qwen）；`probe_all`（smoke 可用性核查）为 v6 新写；审计包装在外层
- `engine/hashing.py`：**算法随 M1 统一改为 SHA-256**（v5 现为 SHA-512；sha512_* → sha256_*，函数签名与调用点不变）——v5 旧产物不进 v6 校验链，无迁移负担

### D. 变更记录
- v1（2026-09-13 中午）：架构讨论稿（R1-R8/角色/成本/里程碑）
- v2（2026-09-13 晚）：**本文档**——详细设计版：模块落位、完整 schema、阶段逐步流程、门禁算法与反例、暂停协议、错误处理、测试计划；并入实例生命周期与文件管理规范
- v3（2026-09-19）：**点将改为“先问后验”**——每次开始建模先问博士（运行时用几个/哪些模型实例：推理池/评审池/主模型），问询完成后只对所选别名做可用性核查、状态表交博士处置；同步修订 §0 / §2.2(R5) / §3.1 / §3.2 / §3.3 / §5.1 / §7 / §8 / §12
- v4（2026-09-19）：哈希口径调整（当日即被 v5 撤销，见下）
- v5（2026-09-19）：**全系统统一 SHA-256**——内容级哈希与 git 对象格式同族、取消分层口径；`MANIFEST.sha256.json`、schema 字段 `sha256`；engine/hashing.py 随 M1 同步统一（见附录 C）
- v6（2026-09-19）：扫尾修订——调用层引用改指 `llm_bridge`/`llm_client`（原 `llm_backend.py` 不存在）、`models.json` 明确为 M1 新建别名层；假设官/DA 挂点落进 P3（分歧＋假设审计三实例）；每问门禁统一为 ①②③⑤；M1 CLI 口径改十个子命令；§3.9 增“双源派生核验”与分场景裁决规则（§12-10）
