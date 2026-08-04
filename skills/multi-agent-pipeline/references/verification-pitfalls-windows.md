# Verification Script Pitfalls (updated 2026-07-11)

## GCM 认证弹窗会卡死后台 push（2026-08-04 实测）

**症状**：`git push` 在后台会话执行时超时无输出——Git Credential Manager 弹了 GUI 登录窗口，但无人点击。

**根因**：凭据过期/丢失后，Windows 的 GCM 以 GUI 弹窗等待认证；后台 terminal 看不到弹窗，push 一直挂起。

**解决**：
1. 检查凭据：`git config --global credential.helper`（应为 `manager`）、`ls ~/.git-credentials`
2. 先 `git config --global credential.helper manager` 确保 GCM 启用
3. push 放后台（`background=true` + `notify_on_complete=true`），**立即告知用户桌面会弹窗，选 "Sign in with your browser"**
4. 用户确认登录后 poll/wait 验证结果，再 `git status -sb` 确认无 ahead

## execute_code ≠ terminal

`execute_code` runs in a **sandboxed temp directory** with limited tool access. It cannot:
- Import project modules (`ModuleNotFoundError`)
- Reliably access project files without absolute paths

**Rule**: For verification scripts that import project code or call local services, write to a `.py` file then `terminal('python file.py')`. Do NOT use `execute_code`.

```python
# ❌ BAD — execute_code can't import project modules
from kimi_client import _extract_json  # ModuleNotFoundError

# ✅ GOOD — write temp script, run via terminal
write_file(path='C:/.../Temp/hermes-verify-fix.py', content='...')
terminal('python C:/.../Temp/hermes-verify-fix.py')
```

## Windows /tmp doesn't exist

`/tmp` is Linux-only. On Windows use:
- `C:\Users\XuXiaoQi_ai\AppData\Local\Temp` (system temp)
- Or project-local paths like `C:\Users\XuXiaoQi_ai\color-transfer-app\backend\uploads`

## curl not guaranteed on Windows

PowerShell's `Invoke-WebRequest` is always available. For `.bat` startup scripts, use:
```batch
powershell -Command "try {$r=Invoke-WebRequest -Uri 'http://localhost:5000/api/health' -TimeoutSec 2; exit 0} catch {exit 1}"
```
Alternative: just `python -c "import requests; requests.get(...)"` if python available.

## Flask debug reload

When `debug=True`, Flask auto-reloads on code changes (via `stat`). The reload kills the old process and spawns a new one. Old `background=true` processes become zombies. After editing server code, either:
1. Let Flask auto-reload (and accept zombie processes)
2. Set `debug=False` for stability
3. Kill and restart manually
