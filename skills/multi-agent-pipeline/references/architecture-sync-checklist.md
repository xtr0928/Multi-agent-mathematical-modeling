# 架构变更后同步清单

> 生成于 2026-07-27，基于 Pipeline v1→v2 升级实战。

## 背景

将 multi-agent-pipeline 从 v1（GLM 分析→Kimi 编码→GLM 审查）升级到 v2（GLM+K3 并行分析→GLM+K3 并行审查）后，发现以下文件仍保留旧引用：

| 文件 | 旧内容 | 影响 |
|------|--------|------|
| SOUL.md L103-117 | Pipeline 仍然是 v1 流程 | 每次新 session 按旧架构执行 |
| SOUL.md L136 | kimi-ocr = Kimi K2.6 | 模型引用错误 |
| architecture-landscape.md L65 | Kimi K2.6，审查列无标记 | 角色矩阵不反映 K3 视觉审查能力 |

## 修复步骤

1. 全文搜索 `K2\.6|k2\.6|kimi-k2\.6` — 全部替换为 K3
2. SOUL.md Pipeline 章节重写，加入 Phase 3b 视觉审查
3. architecture-landscape.md 角色矩阵更新

## 同步规则（已写入 SOUL.md）

修改 Skill 文件后必须同步检查：
1. `SOUL.md` — 模式描述 + 模型表格
2. `references/architecture-landscape.md` — 角色分工矩阵
3. Memory — 模型名/角色描述

## MSYS 路径陷阱

Windows git-bash 下使用 `~/` 或 `/c/` 前缀的路径时，patch 工具可能将路径解析为 `C:\c\Users\...`（双重盘符）。始终使用 `C:\Users\...` 格式。
