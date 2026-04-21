# Local Bootstrap Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the feature branch runnable from a fresh machine with one explicit local-start command and current docs.

**Architecture:** Keep Docker Compose as the only supported runtime path. Add a small root bootstrap script for readiness waiting, expose it through `make dev-up`, and align the README with the Level 1 AI spam-gating architecture.

**Tech Stack:** Bash, Docker Compose, Make, Markdown

---

### Task 1: Replace stale top-level Make targets

**Files:**
- Modify: `Makefile`

**Step 1: Replace old network-bound targets**

Remove stale targets that reference the old Docker network and replace them with:
- `dev-up`
- `dev-down`
- `dev-logs`
- `dev-ps`
- `test-backend`
- `test-gateway`
- `test-frontend`
- `test-e2e`
- `test-all`

**Step 2: Keep commands explicit**

Use the same commands already verified on this branch:
- `PYTHONPATH=backend .venv/bin/pytest backend/tests -q`
- `PYTHONPATH=$(pwd) .venv/bin/pytest vlm_gateway/tests -q`
- `npm --prefix frontend run lint`
- `npm --prefix frontend run test`
- `npm --prefix frontend run build`
- `npm --prefix frontend exec playwright test`

### Task 2: Add a supported bootstrap script

**Files:**
- Create: `scripts/dev_up.sh`

**Step 1: Start the full stack**

Run:
- `docker compose up -d --build db minio redis llama-server vlm-gateway backend frontend`

**Step 2: Wait for readiness**

Poll Docker state until:
- `db`, `minio`, `redis`, `llama-server` are `healthy`
- `vlm-gateway`, `backend`, `frontend` are `running`

**Step 3: Fail fast**

On timeout:
- exit non-zero
- print the current service state
- print the exact `docker compose logs <service>` remediation command

**Step 4: Print operator-facing next steps**

Print:
- frontend URL
- proxied API docs URL
- gateway docs URL
- llama health URL
- MinIO console URL
- seeded user emails
- note about first model download latency

### Task 3: Update root README

**Files:**
- Modify: `README.md`

**Step 1: Refresh quick start**

Document the supported local start command:
- `make dev-up`

**Step 2: Correct behavior descriptions**

Document:
- citizen no longer chooses category during report submission
- AI only decides whether the submission is in scope or rejected
- accepted reports are stored as uncategorized until admin assigns the category
- sysadmin can inspect intake archive and override rejected submissions

**Step 3: Refresh testing section**

Point readers to:
- `make test-backend`
- `make test-gateway`
- `make test-frontend`
- `make test-e2e`

### Task 4: Verify the documented path

**Files:**
- Verify only

**Step 1: Run bootstrap path**

Run:
- `make dev-up`

Expected:
- compose services start
- readiness waits complete
- frontend is reachable at `http://localhost:3011`

**Step 2: Run current validation commands**

Run:
- `make test-backend`
- `make test-gateway`
- `make test-frontend`
- `make test-e2e`

**Step 3: Clean VCS hygiene**

Run:
- `git diff --check`

Expected:
- no whitespace or merge-marker issues
