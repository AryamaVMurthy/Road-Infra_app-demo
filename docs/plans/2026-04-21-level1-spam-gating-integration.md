# Level 1 Spam Gating Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate the Level 1 AI spam-gating flow fully into the MARG system so citizen reports are screened by the separate VLM stack, accepted reports enter the normal workflow uncategorized, rejected reports are archived and auditable, and the full local stack can be started and verified end to end.

**Architecture:** Keep the current separate-service design: `frontend -> backend -> vlm-gateway -> llama-server`, with Redis-backed queueing inside `vlm-gateway`. The AI only makes a binary decision, `IN_SCOPE` or `REJECTED`; category assignment remains a human admin action inside the main system.

**Tech Stack:** FastAPI, SQLModel, Redis, llama.cpp `llama-server`, React/Vite, Playwright, Docker Compose, pytest, Vitest.

---

### Task 1: Lock the integration contract as the system of record

**Files:**
- Modify: `docs/plans/2026-04-21-level1-spam-gating-integration.md`
- Modify: `DESIGN.md`
- Modify: `docs/datasets/vlm_intake_small_v1.md` or active dataset docs if still referenced

**Steps:**
1. Document the canonical Level 1 behavior:
   - AI decides only `IN_SCOPE` or `REJECTED`
   - backend creates issues with `category_id=null`
   - admin assigns category later
2. Remove or mark obsolete any design references to Level 2 runtime classification in active docs.
3. Add one short data-flow section in `DESIGN.md` that names:
   - `llama-server`
   - `vlm-gateway`
   - Redis queue
   - intake archive
4. Verify all docs use the same terms:
   - `REJECTED_SPAM`
   - `ACCEPTED_UNCATEGORIZED`
   - `CATEGORY_ASSIGNED` / `CATEGORY_REASSIGNED`

**Validation:**
- `rg -n "Level 2|two-pass|category detection" docs DESIGN.md backend frontend vlm_gateway`

### Task 2: Make service startup deterministic in local Compose

**Files:**
- Modify: `docker-compose.yml`
- Modify: `vlm_gateway/app/server.py`
- Modify: `vlm_runtime/llama_cpp/start_llama_server.sh`
- Create or modify: `vlm_runtime/llama_cpp/README.md`

**Steps:**
1. Add explicit environment variables for the DSPy Level 1 prompt artifact path used by the live llama-backed classifier.
2. Ensure `vlm-gateway` fails fast on missing model runtime URL or missing DSPy prompt artifact.
3. Add health-check guidance for:
   - Redis
   - `llama-server`
   - `vlm-gateway`
4. Keep queue concurrency at `1` for now.
5. Document the startup order and the expected warm-up behavior.

**Validation:**
- `docker compose up -d redis llama-server vlm-gateway backend frontend`
- `docker compose ps`
- `curl http://localhost:8081/health`
- `curl http://localhost:8090/docs || true`

### Task 3: Harden the gateway-runtime contract around real llama-server behavior

**Files:**
- Modify: `vlm_gateway/app/prompts.py`
- Modify: `vlm_gateway/app/parser.py`
- Modify: `vlm_gateway/app/llama_client.py`
- Modify: `vlm_gateway/tests/test_llama_contract.py`
- Modify: `vlm_gateway/tests/test_live_gateway_contract.py`
- Modify: `vlm_runtime/llama_cpp/smoke_test.py`

**Steps:**
1. Keep the DSPy prompt instructions as the source of truth.
2. Keep the parser strict, but support the real structured text output shape produced by the current llama-server build.
3. Preserve fail-fast behavior for:
   - malformed output
   - unsupported decisions
   - missing rationale
   - invalid category hint
4. Capture raw response payloads in `raw_primary_result` for debugging and audit.
5. Keep latency metrics in the gateway response.

**Validation:**
- `PYTHONPATH=/home/aryamavmurthy/work/MARG/Road-Infra_app-demo/.worktrees/with_AI_filtering ./.venv/bin/pytest vlm_gateway/tests -q`
- `./.venv/bin/python vlm_runtime/llama_cpp/smoke_test.py --image test_e2e.jpg`

### Task 4: Finish backend ownership of the citizen intake path

**Files:**
- Modify: `backend/app/api/v1/issues.py`
- Modify: `backend/app/services/report_intake_service.py`
- Modify: `backend/app/services/vlm_client.py`
- Modify: `backend/app/models/domain.py`
- Modify: `backend/app/schemas/issue.py`
- Modify: `backend/tests/test_vlm_client.py`
- Modify: `backend/tests/test_issue_intake_vlm_flow.py`
- Modify: `backend/tests/test_intake_archive_api.py`

**Steps:**
1. Keep `POST /api/v1/issues/report` free of required category input.
2. Ensure accepted reports:
   - create or merge issue
   - set issue category to `null`
   - set `requires_admin_category_assignment=true`
3. Ensure rejected reports:
   - do not create issue
   - persist archive row
   - write audit event
4. Ensure gateway failures stay explicit:
   - `503`
   - `SYSTEM_ERROR`
   - no fallback classifier
5. Preserve raw classification metadata for admins and audit views.

**Validation:**
- `PYTHONPATH=backend ./.venv/bin/pytest backend/tests/test_vlm_client.py backend/tests/test_issue_intake_vlm_flow.py backend/tests/test_intake_archive_api.py -q`

### Task 5: Complete admin moderation and archive workflows

**Files:**
- Modify: `backend/app/api/v1/admin/issues.py`
- Modify: `backend/app/api/v1/admin/system.py`
- Modify: `frontend/src/pages/authority/AuthorityDashboard.jsx`
- Modify: `frontend/src/features/authority/components/Modals/IssueReviewModal.jsx`
- Modify: `frontend/src/pages/admin/AdminDashboard.jsx`
- Modify: `frontend/src/services/admin.js`
- Modify: `frontend/src/test/IssueReclassifyModal.test.jsx`
- Modify: `frontend/src/test/AdminArchiveTab.test.jsx`

**Steps:**
1. Make uncategorized accepted issues obvious in authority/admin dashboards.
2. Expose one clear admin action to assign category.
3. Expose rejected intake archive to sysadmin users only.
4. Show AI metadata in admin views:
   - decision
   - model id
   - prompt version
   - rationale
5. Audit both:
   - initial AI reject/accept
   - later admin override or category assignment

**Validation:**
- `npm --prefix frontend run test`
- targeted admin API/backend tests if changed

### Task 6: Finish citizen UX for the new intake contract

**Files:**
- Modify: `frontend/src/pages/citizen/ReportIssue.jsx`
- Modify: `frontend/src/test/ReportIssueVlm.test.jsx`
- Modify: `frontend/tests/citizen_rigor.spec.js`

**Steps:**
1. Keep the citizen flow simple:
   - upload photo
   - pin location
   - optional notes
2. Ensure success copy says the report was accepted for review, not categorized.
3. Ensure reject copy is explicit and non-confusing.
4. If useful, add a short “manual review will assign category” message in accepted state.
5. Keep the API shape aligned with the backend response contract.

**Validation:**
- `npm --prefix frontend run test`
- targeted Playwright citizen flow once Docker access is available

### Task 7: Add operational observability and runbooks

**Files:**
- Modify: `vlm_gateway/app/main.py`
- Modify: `vlm_gateway/app/worker.py`
- Modify: `backend/app/services/report_intake_service.py`
- Create or modify: `docs/render_systems_handbook.py`
- Create: `docs/plans/2026-04-21-level1-spam-gating-ops.md`

**Steps:**
1. Emit structured logs for:
   - enqueue
   - dequeue
   - llama request start/end
   - parser contract failure
   - backend accept/reject/system error
2. Add queue-depth and request-latency visibility to logs.
3. Write an operator runbook with:
   - how to start services
   - how to smoke test
   - how to inspect rejected archive
   - how to diagnose `SYSTEM_ERROR`
4. Record the currently observed warm/cold latency ranges.

**Validation:**
- manual end-to-end run with log inspection

### Task 8: Fix the final browser E2E dependency and run the complete gate

**Files:**
- Modify: `frontend/tests/helpers/db.js`
- Modify: Playwright config if needed
- Modify: local run docs if needed

**Steps:**
1. Fix Docker socket discovery for Playwright DB helpers on this machine.
2. Re-run Playwright so the final gate uses the real seeded stack.
3. Verify at least these scenarios:
   - valid image -> accepted -> issue visible uncategorized
   - irrelevant image -> rejected -> archive visible
   - admin assigns category -> issue updates correctly
   - gateway failure -> explicit user-facing failure, no silent fallback

**Validation:**
- `npm --prefix frontend exec playwright test`

### Task 9: Full-stack bring-up and release checklist

**Files:**
- Modify: `README.md`
- Modify: `DESIGN.md`
- Create: `docs/plans/2026-04-21-level1-spam-gating-release-checklist.md`

**Steps:**
1. Write the exact local bring-up steps.
2. Write the exact verification order:
   - backend tests
   - gateway tests
   - frontend lint
   - frontend unit tests
   - frontend build
   - Playwright
3. Document known limitations:
   - binary AI gate only
   - category assignment is human-driven
   - current model quality still needs improvement
4. Add rollback guidance:
   - disable gateway via config
   - stop `vlm-gateway` / `llama-server`
   - restore manual-only intake if required

**Validation:**
- dry-run the checklist once before merge

## Final Verification Order

Run in this order:

1. `PYTHONPATH=/home/aryamavmurthy/work/MARG/Road-Infra_app-demo/.worktrees/with_AI_filtering ./.venv/bin/pytest vlm_gateway/tests -q`
2. `./.venv/bin/python vlm_runtime/llama_cpp/smoke_test.py --image test_e2e.jpg`
3. `PYTHONPATH=backend ./.venv/bin/pytest backend/tests -q`
4. `npm --prefix frontend run lint`
5. `npm --prefix frontend run test`
6. `npm --prefix frontend run build`
7. `npm --prefix frontend exec playwright test`

## Success Criteria

- Citizen reports are screened by the separate VLM stack before issue creation.
- Accepted reports create or merge uncategorized issues only.
- Rejected reports are archived and sysadmin-visible.
- Admins can assign or change categories manually.
- Gateway queueing is active and observable.
- The stack starts from Compose without hidden manual patching.
- All non-environmental validation gates pass.
