# Pipeline Example: Add Reset Password (auth.js)

Concrete demonstration of file-by-file GLM → Kimi → verify pipeline, 2026-07-02.

## Task

Add SMS-based password reset to the scheduler system. Affects one file: `backend/src/routes/auth.js`.

## Phase 1: GLM Analyzes (4m14s)

Prompt to GLM:
```
分析 auth.js，输出针对「添加重置密码功能」的逐行改动清单。
格式：第X行-Y行：改什么 / 第X行后插入：加什么
```

GLM output:
```
改动1 — send-sms 第33-39行: purpose=='reset' 时查 user，未注册→400
改动2 — 第13行后插入: verifySmsCode 辅助函数（从 register 提取校验逻辑）
改动3 — 第155行后插入: POST /reset-password 路由
```

## Phase 2: Kimi Writes (2m48s)

Prompt to Kimi included ONLY the file content + GLM's 3 instructions:

```
修改文件: auth.js
当前文件内容: [full file]
按照 GLM 指示改动:
1. send-sms 加 reset 分支
2. 插入 verifySmsCode helper
3. 插入 /reset-password 路由
只输出完整新文件代码。
```

Kimi produced a 328-line file with all 3 changes applied, leaving login/wechat/refresh/logout/me untouched.

## Phase 3: Skipped (code verified directly)

## Phase 4: Default Verifies

```python
# 1. reset for unregistered phone → 400 "该手机号未注册"
# 2. reset for registered phone → 200, SMS sent
# 3. reset with wrong code → 400 "验证码错误"
# 4. Joi validation → 400 "手机号格式错误"
```

All 4 cases passed.

## Key Takeaways

- GLM's line-number precision matters: `第33-39行` not `send-sms函数`. This lets Kimi be surgical.
- Kimi needs the FULL current file, not a summary. It reads line-by-line to find insertion points.
- One file, one Kimi dispatch. Do NOT batch multiple files into one Kimi call.
- Phase 3 (GLM review) is optional when the change is small and Phase 4 verification covers it.
