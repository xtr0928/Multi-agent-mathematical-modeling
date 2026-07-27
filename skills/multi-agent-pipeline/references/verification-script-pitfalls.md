# Verification Script Pitfalls

Lessons from repeated verification failures in scheduler project.

## 1. Rate Limiter Accumulation

`express-rate-limit` counts persist in the Node process memory. Each test call to login/register/send-sms consumes quota.

**Fix**: Always kill + relaunch backend immediately before verification. Do this in ONE turn so no other calls sneak in.

## 2. Python `and/or` Short-Circuit Bug

```python
# BROKEN — ok() returns None (falsy), so no() ALWAYS fires
(s == 200 and ok("health") or no("health", s))
# FIX
if s == 200: ok("health")
else: no("health", s)
```

## 3. Hardcoded HTTP Status in api() Return

```python
# BROKEN
return json.loads(resp.read()), 200
# FIX
return json.loads(resp.read()), resp.status
```

## 4. api() Parameter Name Mismatch

When writing inline helpers in `execute_code`, inconsistent param names (e.g. `t` vs `token`, `b` vs `body`) cause `TypeError: got unexpected keyword argument`. Always use full word param names: `def api(method, path, body=None, token=None)`.

## 5. SPA Frontend Verification

`curl http://localhost:5173/login` returns Vite's empty HTML shell. React-rendered text does NOT appear in raw HTML. Use `browser_navigate` + `browser_snapshot` for UI checks. Use `curl` only for server-alive check.

## 6. subprocess.run vs terminal() for Build Verification

```python
# BROKEN — Python subprocess can't find npm (not in venv PATH)
subprocess.run(["npm", "run", "build"], cwd=..., timeout=60)
# → FileNotFoundError on Windows

# FIX — use shell=True, or call terminal() tool directly
subprocess.run("npm run build", cwd=..., shell=True, timeout=60)
```

When the verification script is run via `python script.py` (not via terminal tool), `npm` is not on PATH. Use `shell=True` to inherit the system PATH, or split the verification: Python for API tests + terminal tool for build.
