# MCM Problem: Multi-Agent Pipeline Lessons

## 2026-07-02 完整流程

### Phase 0: 3-Agent Parallel Brainstorming (math-brainstorm)

| Agent | 耗时 | 输出 |
|-------|------|------|
| GLM 5.3 | 4m25s | 凸多面体+Shapley+SEM+动态权重 |
| DeepSeek V4 | 2m28s | QP约束+FPI+Z-score+Plackett-Luce |
| Kimi K2.6 | 2m34s | 贝叶斯MCMC+Cox+二次投票+Arrow公理 |
| Merge | 1m20s | 统一方案(标注来源) |

**结论**: 3人并行脑暴高效可靠，6分钟产出完整解题框架。

### Phase 1: GLM 架构分析 (multi-agent-pipeline)

**问题**: 600-word prompt → GLM 300s 超时无输出。

**解决**: 拆成 T1-T4 四个独立 prompt（每个 ≤300 words），并行派发：

| 拆分后 | 耗时 |
|--------|------|
| T1 粉丝票反推 | 5m30s |
| T2 投票方式比较 | 5m07s |
| T3 影响因素分析 | 2m47s |
| T4 公平投票系统 | 2m15s |

**分裂法规则**:
- prompt >400 words → 拆成 ≤300 words 子问题
- 子问题之间不能有依赖关系（不要写"基于T1的结果..."）
- 用 `terminal(background=true)` 并行派发

### Phase 2: Kimi 编码

**问题**: Kimi-coder 卡初始化 3分钟+，T1 甚至搜 Google。

**决策**: 杀掉，切 Phase 1 only → default 独编。

**Default 独编产出**: task1_fan_estimate.py + task2_analysis.py，12分钟内编译运行产出全部结果。

### Phase 3: GLM 审查

**问题**: Kimi 代码没产出 → Phase 3 跳过。

**补救**: 用已有代码的数据让 GLM 审查数学正确性（已完成 T3 T4）。

### 最终交付

- fpdf2 中文 PDF: 11 页，823KB
- 5 张配图 (matplotlib 300dpi)
- 与 Meritorious Winner 方法论一致

## 关键教训

1. **GLM 天然慢但不是不能用**: 4-5 分钟正常，拆 prompt 是唯一靠谱方法
2. **Kimi 编码不可靠**: 初始化慢、会搜 Google、不适合数学建模代码
3. **用户急了 → Solo**: 立即去掉所有外部依赖，直接出活
4. **数模脑暴用 math-brainstorm**: 3人并行比单人更全面
5. **编码走 default**: DeepSeek 写数模代码比 Kimi 更快更准
