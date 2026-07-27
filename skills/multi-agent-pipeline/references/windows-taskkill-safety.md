# Windows: `taskkill //F //IM node.exe` Danger

## Problem

On Windows, `taskkill //F //IM node.exe` kills **all** node.exe processes on the machine, including:
- Dashboard server (intended target)
- Hermes Agent's own sub-processes (unintended)
- Any other node-based tools running

This can crash Hermes mid-conversation.

## Safe Alternatives

### Option 1: Kill by port (best)
```bash
# Find PID listening on port, kill only that
FOR /F "tokens=5" %a IN ('netstat -ano ^| findstr ":14514.*LISTENING"') DO taskkill //F //PID %a
```

### Option 2: Kill by window title
```bash
taskkill //FI "WINDOWTITLE eq Dashboard*" //F
```

### Option 3: Save PID on start, kill by PID
```bash
node server.js & echo $! > dashboard.pid
kill $(cat dashboard.pid)
```

### Option 4: Use netstat first (manual)
```bash
# Always check what you're about to kill
netstat -ano | findstr ":14514"
# Then kill only that specific PID
taskkill //F //PID <specific_pid>
```

## What NOT to do
```bash
# ❌ NEVER do this — kills Hermes itself
taskkill //F //IM node.exe
```

## Bash/MSYS Notes
- `//FI` syntax doesn't work in git-bash/msys — use just the command name
- `tasklist` without filters works in bash; filter with `grep` instead
- Windows `findstr` equivalent in bash: `grep`
