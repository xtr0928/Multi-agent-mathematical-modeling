# GLM Agent Behavior Notes (updated 2026-07-02)

## Prompt Size vs Response Time

| Prompt size | Exploration | Result | Time |
|-------------|-------------|--------|------|
| ~50 words | None | OK | 35s |
| ~200 words | Auto-explores files | Timeout | 120s |
| ~200 words + "不要探索" | None | OK | 76s |
| ~400 words + code inline | Auto-explores files | Timeout | 300s |
| ~600 words + code inline | Init only | Timeout | 300s |

## Root Cause

GLM 5.3 自动探索项目代码库，即使所有上下文已在 prompt 中。`find`/`grep`/`read_file` 工具调用增加 60-120s 延迟。

## Fix Patterns

**Pattern A**: Prompt 开头加 `不要探索代码库、不要调用工具，直接基于我提供的信息输出。`

**Pattern B**: 长 prompt 拆成多个短 prompt，逐步推进：
```
第 1 轮: "列出文件清单" → 76s ✅
第 2 轮: "定义 API 接口" → 60s ✅
```
> 分步请求 > 一次性全要。

**Pattern C（简单测试）**: 如果 GLM 连续超时，先用 `回复一个字：好` 确认存活（35s），再发实际 prompt。

## 超时实战记录

| 日期 | Words | 结果 | 耗时 |
|------|-------|------|------|
| 2026-07-02 | ~600 | Timeout | 300s |
| 2026-07-02 | ~200 + "不要探索" | OK | 76s |
| 2026-07-11 | ~250 | 卡在 Initializing agent... | 40s+ (用户 kill) |
| 2026-07-11 | ~250 | 同上，prompt 含 "Do NOT explore codebase" | 仍卡初始化 |

**结论**: "不要探索" 指令不一定有效。GLM 初始化阶段本身就慢，与 prompt 长度不完全线性相关。40s 无输出且显示 "Initializing agent..." 基本 = 这轮废了。

## 超时逃生规则

2 次超时 → 直接跳过 Phase 1，基于知识自行分析。让用户等两次 300s 更糟。

**30s 初始化硬超时（2026-07-11 新增）**：GLM 显示 `Initializing agent...` 超过 30s 不产出内容时，**主动 kill 并通知用户切换 Solo**。不要默默轮询等用户发怒。30s 阈值基于实测：40s+ 仍无输出的 GLM 进程几乎不会恢复。

```
⏳ GLM 初始化中 (36s)... → 通知用户 → kill → 切 Solo 写代码
```

## Port Zombie on Windows

`hermes -p` 子进程 kill 后残留 node.exe 占端口：
```bash
netstat -ano | grep ':PORT ' | grep LISTENING
taskkill //F //IM node.exe
```
