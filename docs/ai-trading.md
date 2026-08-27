# GitHub AI 股票交易项目全景调研（53 项目深度分析）

> 2026-08-12 · 搜索 98 候选 → 下载 53 个（150★+）→ 全部深度分析
> 数据源：GitHub Search API + 本地仓库 README/源码逐文件精读（主代理 14 个 + 3 子代理 39 个并行）

## 一、生态全貌（53 个已下载项目）

### 头部梯队（10k★+）

| 项目 | ★ | 流派 | 一句话 |
|------|:--:|------|------|
| TauricResearch/TradingAgents | 97.7k | 多团队+辩论 | 行业标杆：5 分析师→多空辩论→3 风控人格→组合管理→交易员 |
| hsliuping/TradingAgents-CN | 31.1k | 辩论（中文） | 中文增强版，v1.0 开源 v3.0 闭源商业 |
| HKUDS/Vibe-Trading | 30.7k | 研究台+swarm | 港大：9 回测引擎 + 462 因子 Alpha Zoo + 24 数据源 + 影子账户 |
| HKUDS/AI-Trader | 21.3k | 平台型 | Agent-Native 交易平台：发消息即接入（SKILL.md 契约） |
| xbtlin/ai-berkshire | 15.5k | 多团队（价值） | 四大师方法论对抗 + 强制结论 + 实盘 +69%/+66% |
| OpenByteInc/QuantDinger | 10.5k | 交易 OS | 想法→策略→回测→实盘→监控 全栈自托管 |

### 中坚梯队（1k-10k★）

| 项目 | ★ | 流派 | 一句话 |
|------|:--:|------|------|
| AI4Finance-Foundation/FinRobot | 7.8k | 流水线+辩论 | FinGPT 作者的 Agent 平台（LLM+RL+量化） |
| LuckyOne7777/LLM-Trading-Lab | 7.5k | 实验记录 | ChatGPT 真钱管理 6 个月实验，全数据可审计 |
| TraderAlice/OpenAlice | 6.5k | agent-native 工作区 | 一人华尔街：审批门控交易原语 |
| charliedream1/ai_quant_trade | 6.1k | 工具集/教程 | A 股全栈学习资源（含 RL 回测） |
| 1nchaos/adata | 5.1k | 数据基建 | 免费 A 股量化数据库 |
| The-Swarm-Corporation/AutoHedge | 4.2k | swarm 对冲基金 | Director→验证→风控→执行；Solana 全自动 |
| Polymarket/agents | 3.8k | 工具集 | 预测市场官方框架 + RAG |
| simonlin1212/TradingAgents-astock | 2.8k | 辩论（A 股） | TA 的 A 股特化 fork：7 分析师按 A 股规则辩论 |
| chrisworsey55/atlas-gic | 2.1k | 自进化+商业化 | Copy trading + Agent marketplace + Kalshi 60% 胜率 |
| simonlin1212/Vibe-Research | 2.0k | 辩论（合规） | 底稿制辩论，禁推荐禁点位 |
| Lumiwealth/lumibot | 1.9k | 回测执行 | 可回测 AI 交易 agent 框架 |
| oficcejo/aiagents-stock | 1.8k | 多 agent 团队 | 模拟证券分析师团队 + 龙虎榜跟踪 |
| ginlix-ai/LangAlpha | 1.6k | 工具集 | Claude Code for Financial Market（PTC 沙箱） |
| mnemox-ai/tradememory-protocol | 1.4k | 记忆层 | 决策审计 + 结果加权记忆（已维护模式） |
| ZhangJinHaHaHa/AgentLens | 1.0k | 平台/合约 | 链上审计 agent 市场（非策略） |

### 长尾（150-1k★）：FinMem 936 / MAHORAGA 864 / PanWatch 773 / AShare 766 / prism-insight 717 / nof1.ai 684 / ContestTrade 677 / CloddsBot 661 / ai-hedge-fund-crypto 616 / llm-agent-trader 440 / mcp-aktools 390 / moss-trade-bot 367 / circuit-framework 353 / alphasift 338 / vibe-investing 323 / LLM-TradeBot 311 / CryptoTradingAgents 274 / finnts 266 / FinSight 258 / AlpacaTradingAgent 248 / TwinMarket 207 / multi-agent-investment 201 / Equibles 195 / alphaevo 181 / vibe-astock 177 / InvestSkill 171 / AgentQuant 171 / gym-continuousDoubleAuction 154

## 二、架构流派分类（53 项目）

| 流派 | 数量 | 代表 | 核心思想 |
|------|:--:|------|------|
| **辩论式**（多空/多角色对抗） | 7 | TradingAgents 系 ×5、AShare、Vibe-Research | 对抗产生信息张力，风控人格制衡 |
| **多团队并行** | 5 | ai-berkshire、prism-insight、aiagents-stock、FinRobot | 多视角独立分析后融合 |
| **流水线式**（研究→决策→执行） | 8 | QuantDinger、FinSight、llm-agent-trader、circuit-framework | 阶段化串行，确定性风控门 |
| **内部竞赛** | 2 | ContestTrade、TwinMarket | 提案互相 PK / 市场仿真 |
| **自进化/记忆** | 4 | FinMem、atlas-gic、alphaevo、tradememory | 结果反馈→记忆/策略迭代 |
| **工具/Skill 集** | 12 | ai-berkshire、LangAlpha、CloddsBot、InvestSkill、moss | 给已有 agent（Claude/Codex）加能力 |
| **平台/契约化** | 4 | AI-Trader、AgentLens、swapper、AI-Trader | agent 间 API 标准化（SKILL.md/合约） |
| **数据/基建** | 6 | adata、lumibot、Equibles、mcp-aktools、quantconnect | 数据层/回测层独立 |
| **RL/仿真** | 3 | gym-continuousDoubleAuction、StockSim、TwinMarket | 强化学习/市场模拟 |

## 三、提示词工程亮点（逐条摘录，带出处）

1. **强制给结论不打太极**（ai-berkshire）：「普通 AI 回答：'有增长潜力但也面临竞争压力' → AI Berkshire 输出：激进型 $95-105 建仓 20% / 稳健型等回购明确 / 保守型观望」+ **镜子测试**：5 句话说不完整 = 不买
2. **多空直接对话而非罗列**（TradingAgents bull_researcher）：「engaging directly with the bear analyst's points and debating effectively **rather than just listing data**」
3. **禁模糊表述**（prism-insight）：禁止 vague-hedge 理由，buy_score 评分卡强制数字
4. **合规写进 prompt**（Vibe-Research/vibe-astock）：明令"不推荐、不给点位"，辩论只产出分歧与验证清单
5. **人格/信念注入**（FinMem 风险人格切换、ContestTrade belief_list、CAN SLIM 人格）
6. **结构化裁决约束**（AShare VERDICT JSON 输出、FinMem JSON 记忆索引）
7. **确定性计算与 LLM 叙述分离**（FinRobot："数字由代码算、叙述由 LLM 写"；multi-agent-investment 决策零 LLM）

## 四、回测能力（普遍短板，重大发现）

- **53 个项目中仅 ~7 个有真正回测引擎**：Vibe-Trading（9 引擎）、QuantDinger、lumibot、ai-hedge-fund、llm-agent-trader、ai_quant_trade、tradememory
- 多数项目止步于"研究/信号"层，LLM 决策质量无法量化验证
- 多个项目**无回测直接上实盘**（nof1.ai、MAHORAGA、CloddsBot）——风控薄弱
- 实盘收益宣传（ai-berkshire +69%、LLM-Trading-Lab）均无第三方审计

## 五、对 Multi-Agent 体系的启示（差距清单）

| 能力 | 参考项目 | 价值 |
|------|------|------|
| 462 因子 Alpha Zoo | Vibe-Trading | 回测因子库开箱即用 |
| 24 源数据 fallback 链 + 单位校验 | Vibe-Trading | 数据可靠性工程（2026-08 修 volume 100× bug）|
| 影子账户（日志→诊断→审计）| Vibe-Trading | 交易行为自省闭环 |
| SKILL.md 平台契约 | AI-Trader | agent 接入标准化（与我们 Multi-Agent skill 体系同构！）|
| 四大师方法论对抗 | ai-berkshire | 多视角张力设计（与数模多建模手辩论同源）|
| 强制结论 + 价格区间 | ai-berkshire | 反"和稀泥"输出（与评委 skill 数字强制同源）|
| 确定性风控门 | circuit-framework | 决策与 LLM 分离（与数模证据门禁同构）|
| 内部竞赛优选 | ContestTrade | 提案 PK 机制（与数模五人评审团同构）|

## 六、附注

- **空壳警示**：cortex-sentinel-trading-nexus 零代码纯营销页（README + index.html + preview.svg），已标注
- 所有数据来自真实下载仓库的 README/源码读取，无编造指标
- 完整笔记：`/tmp/aitrading_notes_{0,1,2,main}.md`（~80KB）
