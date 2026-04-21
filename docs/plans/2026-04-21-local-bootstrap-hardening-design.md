# Local Bootstrap Hardening Design

## Goal

Make the `with_AI_filtering` branch runnable from a fresh machine with one obvious local-start command and current documentation, without relying on hidden repo knowledge.

## Chosen Approach

Use a single repo-level entrypoint, `make dev-up`, backed by a small shell script that:

- starts the full Docker Compose stack required by the Level 1 AI intake flow
- waits for dependency health instead of returning immediately
- prints the actual URLs and seeded accounts a developer needs next

This keeps the startup path aligned with the real runtime architecture already used by the branch:

- `frontend`
- `backend`
- `redis`
- `vlm-gateway`
- `llama-server`
- `db`
- `minio`

## Why This Approach

### Option 1: README-only refresh

This improves discoverability but still leaves startup behavior implicit. A fresh user still has to know when the stack is actually ready and which services matter.

### Option 2: Makefile-only alias

This gives a short command but still returns as soon as `docker compose up -d` exits, which is not enough when `llama-server` may still be downloading the GGUF model.

### Option 3: Makefile alias plus readiness script

This is the smallest option that materially improves operability. The Makefile provides the one-command UX, while the script provides the startup guarantees and explicit failure messages.

## Scope

- rewrite the root `Makefile` to reflect current branch commands
- add a supported local bootstrap script
- update the root `README.md` so the documented flow matches Level 1 AI spam screening and admin-side category assignment

## Non-Goals

- no new deployment platform
- no production orchestration changes
- no model/runtime behavior changes
- no new local non-Docker startup path
