# SMS Registration Pattern

Reusable pattern for implementing SMS verification code registration in Express + Prisma apps.

## Dual-Mode Architecture

```
SMS_MODE=mock  → console.log the code (dev)
SMS_MODE=aliyun → real Alibaba Cloud SMS (prod)
```

The `sendSms()` function picks the provider based on `SMS_MODE` env var. This avoids coupling to any specific SMS provider.

## Database: SmsCode Model

```prisma
model SmsCode {
  id         String   @id @default(uuid())
  phone      String
  codeHash   String   // SHA256(code + JWT_SECRET as salt)
  purpose    String   @default("register")
  consumed   Boolean  @default(false)
  attempts   Int      @default(0)
  expiresAt  DateTime
  createdAt  DateTime @default(now())
  userId     String?
  user       User?    @relation(fields: [userId], references: [id])

  @@index([phone, createdAt])
}
```

## Security Layers

| Layer | Mechanism |
|-------|-----------|
| Rate limit | Same phone within 60s → 429 with retryAfter |
| Code hash | SHA256(code + salt), never store plaintext |
| Expiry | 5 minutes, DB `expiresAt` field |
| Anti-replay | `consumed=true` after successful verification |
| Brute force | Max 5 attempts per code, then auto-lock |
| Phone validation | Regex `/^1[3-9]\d{9}$/`, store as E.164 |
| Duplicate check | Before sending, query User table for existing phone (register purpose) |

## API Surface

```
POST /api/auth/send-sms   { phone, purpose }  → 200 | 429 | 409
POST /api/auth/register   { phone, smsCode, password, username }  → 201 | 400
POST /api/auth/login      { account }  // phone OR username + password
```

## Mock Mode

In mock mode, the code is printed to the backend console:
```
📱 [SMS Mock] 发送到 13800138000: 验证码 636129
```

To switch to production: set `SMS_MODE=aliyun` + Alibaba Cloud credentials in `.env`.

## Verification Gotcha

When testing the SMS flow via scripts, note that SMS codes are stored as SHA256 hashes. You cannot reverse them. Two approaches to testing:
1. **Read the code from backend process output** (`process(action='log')`) in mock mode
2. **Brute-force match** the hash against 6-digit candidates (1M hashes, ~2s in Python) — only needed when backend console isn't accessible
