# 数模 Multi-Agent 架构全景

> 生成于 2026-07-11，基于实际配置和实战经验。

## 三套架构总览

```
         ┌─────────────────────────────────────────────────┐
         │          数模 Multi-Agent 架构矩阵              │
         ├──────────────┬──────────────┬───────────────────┤
         │ math-brain   │ brute-force  │ multi-agent-      │
         │ storm        │ think        │ pipeline          │
         │ (脑暴发散)    │ (暴力求解)   │ (编码实现)         │
         ├──────────────┼──────────────┼───────────────────┤
         │ 深度: ★★☆    │ 深度: ★★★    │ 深度: ★★☆         │
         │ 轮次: 1 轮   │ 轮次: 3-4 轮 │ 轮次: 顺序流水线   │
         │ 时间: ~6min  │ 时间: ~15min │ 时间: 按文件数     │
         │ 场景: 思路   │ 场景: 竞赛   │ 场景: 开发         │
         └──────────────┴──────────────┴───────────────────┘
```

## 架构文件位置

| 架构 | 路径 | 文件数 |
|------|------|:--:|
| math-brainstorm | `skills/data-science/math-brainstorm/SKILL.md` | 2 |
| brute-force-think | `skills/data-science/brute-force-think/SKILL.md` | 2 |
| multi-agent-pipeline | `skills/multi-agent-pipeline/SKILL.md` | 12 |

## 串联关系

```
                    ┌─────────────────┐
                    │   一道数模题     │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              │
    ┌─────────────┐  ┌─────────────┐       │
    │ math-brain  │  │ brute-force │       │
    │ storm       │  │ think       │       │
    │ (思路发散)   │  │ (竞赛解题)   │       │
    └──────┬──────┘  └──────┬──────┘       │
           │                │              │
           └────────┬───────┘              │
                    ▼                      │
         ┌──────────────────┐             │
         │  解题方案/思路    │             │
         └────────┬─────────┘             │
                  ▼                       │
    ┌──────────────────────────┐          │
    │  multi-agent-pipeline    │◄─────────┘
    │  (编码实现 + 图表生成)    │
    └────────────┬─────────────┘
                 ▼
    ┌──────────────────────────┐
    │  5writing + 6verity      │
    │  (论文撰写 + 验收)        │
    └──────────────────────────┘
```

## Agent 角色分工矩阵

| Profile | 模型 | 脑暴 | 暴力思考 | 编码 | 分析 | 审查 | 编排 |
|---------|------|:--:|:------:|:--:|:--:|:--:|:--:|
| default | DeepSeek V4 Pro | ✅ | ✅ | 🔧 | - | - | 🎯 |
| glm-review | GLM 5.3 | ✅ | ✅ | - | ✅ | ✅ | - |
| kimi-ocr | Kimi K3 | ✅ | ✅ | - | ✅ | ✅ | - |
| kimi-coder | Kimi K2.7 | ❌ | ❌ | ✅ | - | - | - |

> ⚠️ Kimi K3 视觉审查 / K2.7 编码，不能混用。

## 6 阶段论文流水线

```
1start-mathmodel (总控)
  │
  ├─ ① 2analysis-modeling → ANALYSIS_MODELING_REPORT.md
  ├─ ② 3coding-visual     → code/ + figures/ + RESULTS_REPORT.md
  ├─ ③ 4drawio            → figures/*.drawio + *.pdf
  ├─ ④ 5writing           → paper/ (Typst / LaTeX, 14中+3英模板)
  └─ ⑤ 6verity            → VERIFY_REPORT.md
```

## 架构选择速查

| 用户意图 | 选用架构 |
|---------|---------|
| "给个思路"/"怎么建模" | math-brainstorm |
| "正式解题"/"竞赛" | brute-force-think |
| "写代码"/"实现"/"开发" | multi-agent-pipeline |
| "全流程"/"从题到论文" | 6阶段 Pipeline |

## 编排者 SOUL 配置

编排者 (default / DeepSeek V4 Pro) 的 SOUL.md 位于 `~/AppData/Local/hermes/SOUL.md`，
包含启动协议、三架构加载、进度汇报规则、Kimi bug 清单、Prisma 规范、错误处理等。
