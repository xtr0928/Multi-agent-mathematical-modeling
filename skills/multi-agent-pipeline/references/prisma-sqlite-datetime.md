# Prisma + SQLite 常见坑

## DateTime 类型冲突

### 症状

```
Inconsistent column data: Could not convert value "1782987805000" of the field `createdAt` to type `DateTime`.
```

即使用 `new Date()` 或 `.toISOString()`，Prisma 都报此错。

### 根因

SQLite 表是手动 `CREATE TABLE` 建的，`createdAt` 列类型是 `TEXT`。Prisma schema 定义为 `DateTime`，内部转成 Unix 毫秒数存入 TEXT 列时 SQLite 拒绝。

### 解决方案

改 schema 用 `String`，传 `.toISOString()`：

```prisma
model CodeChange {
  createdAt String @default("")
}
```

```js
data: { ..., createdAt: new Date().toISOString() }
```

### 触发条件

- 手动 SQL 建表 + Prisma schema 定义该表
- 共享数据库（`DATABASE_URL` 指向他人 SQLite 文件）

---

## Git log 日期解析

### 症状

`git log --format="%ai"` 输出 `2026-07-02 18:23:25 +0800`，`new Date()` 返回 `Invalid Date`。

### 修复

```js
const date = new Date(dateStr.slice(0, 19).replace(' ', 'T'));
```

截掉时区（取前 19 字符 `YYYY-MM-DD HH:MM:SS`），替换空格为 `T`。自动转 UTC，展示 commit 时间足够。

### 注意

`git show --stat` 比 `--numstat` 更易解析：`--stat` 输出 `file | 3 ++--` 格式，用正则 `/^\s*(.+?)\s+\|\s+(\d+)\s*(\+*)(-*)/` 提取文件名和增减行数。`--numstat` 遇到二进制文件会输出 `-` 而非数字，需额外处理。

---

## Zombie 端口占用

Windows 上 `hermes -p` 子进程 kill 后残留 node.exe 占端口：

```bash
# 查看 :14514 占用
netstat -ano | grep ':14514 ' | grep LISTENING

# 全杀 node
taskkill //F //IM node.exe
```

每次重启前先 `taskkill`，再启动。
