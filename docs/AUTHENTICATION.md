# Authentication and OTP Guide

## Overview

MARG uses OTP-based login with cookie-based JWT session management.

Authentication flow:

1. Client requests OTP (`/api/v1/auth/otp-request`).
2. User submits OTP (`/api/v1/auth/login`).
3. Backend sets HttpOnly cookies:
   - `access_token`
   - `refresh_token` (scoped to `/api/v1/auth`)
4. Frontend resolves active user through `/api/v1/auth/me`.

## Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/auth/otp-request` | POST | Generate OTP and trigger delivery |
| `/api/v1/auth/login` | POST | Verify OTP and set auth cookies |
| `/api/v1/auth/refresh` | POST | Rotate refresh token and renew access token |
| `/api/v1/auth/logout` | POST | Clear auth cookies |
| `/api/v1/auth/me` | GET | Return current authenticated user |

## OTP Delivery Modes

### DEV mode (`DEV_MODE=true`)

- OTP is generated and stored.
- Email sending is intentionally skipped.
- OTP is printed in backend logs.

### Non-dev mode (`DEV_MODE=false`)

- Backend attempts SMTP send using:
  - `MAIL_SERVER`
  - `MAIL_PORT`
  - `MAIL_USERNAME`
  - `MAIL_PASSWORD`
  - `MAIL_FROM`

If SMTP is misconfigured, OTP generation still occurs but delivery can fail.

## Security Characteristics

- Access and refresh tokens are HttpOnly cookies, reducing token theft via XSS.
- Refresh tokens are persisted as secure hashes (bcrypt) with deterministic lookup hashes (sha256).
- Refresh rotation and token-family logic are implemented in `backend/app/services/auth_service.py`.
- Logout revokes the presented refresh token server-side before clearing cookies.
- Concurrency and breach behavior are tested in backend auth/concurrency tests.

## Operational Checks

### Check OTP in dev logs

```bash
docker compose logs backend --tail=200 | grep -i otp
```

### Validate current session

```bash
curl -i http://localhost:3011/api/v1/auth/me
```

### Validate refresh

```bash
curl -i -X POST http://localhost:3011/api/v1/auth/refresh
```
