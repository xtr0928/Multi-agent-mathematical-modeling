# 本地部署说明（Windows）

## 已完成
- `git clone` 到 `C:\Users\XXQ0928\Multi-agent-mathematical-modeling`
- 依赖：**纯 Python 标准库**，无 requirements.txt/pip 安装。
- 修复 Windows 兼容性：7 处 `os.rename` → `os.replace`
  （`engine/registry.py`、`assumptions/officer.py`、`bench/internal_benchmark.py`、
  `cpp/executor.py` ×2、`cpp/ks_compare.py`、`state/state_machine.py`）；
  原代码 tmp+rename 在 Windows 上遇目标已存在会报 WinError 183。
- 验收测试 **34/34 通过**（tests/ 下 5 个文件，`python tests/<name>.py` 逐个运行）。
- 新增：
  - `pipeline/llm_bridge.py` —— 生产后端桥：自动加载协同编码管线的 `llm_client.py`
    （Multi-agent-programming-pipeline/pipeline/llm_client.py），接口与
    orchestrator `LLMClient(backend=...)` 完全匹配。
  - `pipeline/run_demo.py` —— S0-S6 真实运行器（自动打印预估 LLM 调用次数）。
  - `.gitignore` 增加 `.env`。

## API key 状态（2026-09-09 实测）
从本机 Hermes 凭据（`AppData/Local/hermes/.env`）接通，共享配置
`../Multi-agent-programming-pipeline/pipeline/.env`：
- DEEPSEEK_API_KEY ✓ 实测连通（deepseek-v4-pro）
- GLM_API_KEY ✓ 实测连通（open.bigmodel.cn，glm-5.3；llm_client 已支持 GLM_BASE_URL 可切 z.ai）
- KIMI_API_KEY ✓ 实测连通（api.moonshot.cn，kimi-k2.7-code；取自已配的 KIMI_CN_API_KEY）
- QWEN_API_KEY ✓ 已接通（`ALIBABA_TOKEN_PLAN_CN_API_KEY`，sk-ws- 开头实测连通
  dashscope.aliyuncs.com/compatible-mode/v1 @ qwen3.8-max）
- 四模型 4/4 实测连通完成（deepseek-v4-pro / glm-5.3 / kimi-k2.7-code / qwen3.8-max）。

## 使用

```bash
# 零成本验证（DryRun，不调 API）
cd pipeline && python run_demo.py --problem <题目.txt> --dry-run

# 真实运行（S0-S6 全流程，约 30 次 LLM 调用，运行前有成本提示）
cd pipeline && python run_demo.py --problem <题目.txt> --owner-mode auto
#       半自动拍板（等博士确认）: --owner-mode semi
```

单元测试（随时可跑）：
`cd pipeline && for t in test_engine test_stages test_remaining test_completion test_layout_gates; do python tests/$t.py; done`
