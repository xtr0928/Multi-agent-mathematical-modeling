# Kimi K2.7 Coder Pitfalls (updated 2026-07-02)

## Prisma Import Destructuring Bug

Kimi K2.7 **固定**写成:
```javascript
const { prisma } = require('../config/database');
```

但 database.js 导出的是:
```javascript
module.exports = prisma;  // 单个对象，不是 { prisma }
```

结果 `prisma` 为 `undefined`。**修复**：grep `const { prisma }` 替换为 `const prisma = require(...)`。

## Query Param 拼写错误

Kimi 有时用 `req.query.day` 而不是约定的 `req.query.days`。修复：grep 检查。

## $queryRaw vs $queryRawUnsafe

Kimi 对含 `${var}` 插值的 SQL 用 `$queryRaw`（仅接受 Prisma.sql tagged template），应改为 `$queryRawUnsafe`。

## Module Exports Shape

Kimi 导出裸函数时调用方期望 `{ fn }`：
```javascript
// Kimi: module.exports = authenticate;
// 调用方: require('./auth').authenticate  → undefined
```
**修复**：确保 `module.exports = { authenticate }`。

## Prisma Model 名下划线

Kimi 用 `prisma.code_changes.findMany()`，但 Prisma 自动 camelCase：`prisma.codeChange.findMany()`。

## require.main === module 检查

Kimi 会在 server.js 中加：
```js
if (require.main === module) {
  app.listen(PORT, ...);
}
```
当被根文件 `require('./src/server')` 加载时，不会执行 listen。直接 `app.listen(PORT, ...)`。

## Verification Loop Stuck

Kimi 子进程卡在验证阶段（装依赖、跑测试），但文件已写对且 `node --check` 通过。看到文件已写入就 kill 子进程。

## Phase 4 修复策略（快于 Phase 3 审查）

```bash
grep -rn 'const { prisma }' src/      # Bug #1
grep -rn '\$queryRaw\`' src/           # Bug #3（有 ${} 就改 Unsafe）
grep -rn 'code_changes\|codeChanges' src/  # Bug #5
grep -rn 'module.exports = [^{]' src/  # Bug #4
```
