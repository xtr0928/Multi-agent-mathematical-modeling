# Prisma + SQLite UTF-8 Chinese Encoding Bug

## Problem

On Windows + SQLite, `prisma.$queryRawUnsafe` with parameterized placeholders corrupts Chinese UTF-8 text:

```js
// ❌ BROKEN — Chinese becomes garbled (乱码)
await prisma.$queryRawUnsafe(
  `INSERT INTO code_logs (summary) VALUES (?)`,
  "添加看门狗功能"  // stored as: "添加看门狗功能" in DB
);
// Actually stored as: "���ӿ��Ź�����" (garbled)
```

The parameterized path through Prisma's SQLite connector loses UTF-8 encoding on Windows.

## Fix

Use `prisma.$executeRawUnsafe` with values embedded directly in the SQL string, escaping single quotes:

```js
// ✅ WORKS — Chinese preserved correctly
const esc = (s) => (s || '').replace(/'/g, "''");
await prisma.$executeRawUnsafe(
  `INSERT INTO code_logs (id, summary, reason) 
   VALUES ('${id}', '${esc(summary)}', '${esc(reason)}')`
);
```

## Verification

```js
// Confirm storage
const rows = await prisma.$queryRawUnsafe('SELECT summary FROM code_logs LIMIT 1');
console.log(rows[0].summary); 
// Should output: "添加看门狗功能" (not garbled)
```

## When This Applies

- Windows + SQLite + Prisma + Chinese/UTF-8 text
- Any place where `$queryRawUnsafe(?, [...params])` is used with CJK characters
- Applies to both INSERT and UPDATE operations

## Root Cause

Prisma's SQLite parameter binding on Windows does not preserve the full UTF-8 byte sequence for multi-byte characters. Direct string interpolation into SQL avoids the parameter binding layer entirely.

## Security Note

The `esc()` function prevents SQL injection by doubling single quotes. For production use with user-supplied input, consider switching to PostgreSQL or MySQL where parameterized UTF-8 works correctly.
