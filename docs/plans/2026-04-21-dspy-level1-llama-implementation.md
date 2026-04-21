# DSPy Level 1 Llama Runtime Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the live `llama-server` intake classifier use the exact DSPy Level 1 GEPA prompt in a single-pass runtime, while keeping the current Level 1 backend contract.

**Architecture:** `vlm-gateway` will load the saved DSPy Level 1 GEPA program artifact, extract its exact instructions, and build a single OpenAI-compatible multimodal request for `llama-server`. The backend will continue to receive the existing binary spam-gating result shape.

**Tech Stack:** FastAPI, Redis, httpx, llama.cpp server, DSPy artifact loading, pytest

---

### Task 1: Lock the DSPy prompt extraction contract

**Files:**
- Create: `vlm_gateway/tests/test_dspy_prompt_source.py`
- Modify: `vlm_gateway/app/prompts.py`

**Step 1: Write the failing test**
- Assert the loader can read the GEPA Level 1 artifact and return the exact optimized instruction string.
- Assert startup fails explicitly if the DSPy prompt artifact path is missing.

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/pytest vlm_gateway/tests/test_dspy_prompt_source.py -q`

**Step 3: Write minimal implementation**
- Add a prompt-source loader that reads the compiled DSPy Level 1 program artifact and extracts `predictor.signature.instructions`.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/pytest vlm_gateway/tests/test_dspy_prompt_source.py -q`

### Task 2: Remove the two-pass llama runtime

**Files:**
- Modify: `vlm_gateway/tests/test_llama_client.py`
- Modify: `vlm_gateway/app/llama_client.py`
- Modify: `vlm_gateway/app/prompts.py`

**Step 1: Write the failing test**
- Assert the llama classifier performs only one request.
- Assert the request body uses the DSPy-derived instructions.
- Assert the response still maps to `IN_SCOPE` / `REJECTED` with `category_name = null`.

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/pytest vlm_gateway/tests/test_llama_client.py -q`

**Step 3: Write minimal implementation**
- Delete the description step.
- Build a single multimodal request from the DSPy prompt source.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/pytest vlm_gateway/tests/test_llama_client.py -q`

### Task 3: Add runtime speed improvements

**Files:**
- Modify: `vlm_runtime/llama_cpp/start_llama_server.sh`
- Modify: `docker-compose.yml`
- Modify: `vlm_runtime/llama_cpp/README.md`

**Step 1: Write the failing test**
- Add a focused test or smoke assertion for image preprocessing defaults if needed.
- Otherwise use a documented live verification gate for latency.

**Step 2: Run test or smoke verification to confirm baseline**

Run: existing smoke test and one live gateway request; record latency.

**Step 3: Write minimal implementation**
- Resize images before inference.
- Reduce context size.
- Increase CPU threads and batch threads.

**Step 4: Re-run smoke verification**

Run: live smoke and manual negative/positive gateway calls again.

### Task 4: Re-verify the live Level 1 path

**Files:**
- Modify only if test expectations changed

**Step 1: Run gateway tests**

Run: `PYTHONPATH=. .venv/bin/pytest vlm_gateway/tests/test_prompt_schema.py vlm_gateway/tests/test_llama_contract.py vlm_gateway/tests/test_llama_client.py vlm_gateway/tests/test_live_gateway_contract.py -q`

**Step 2: Run backend tests**

Run: `PYTHONPATH=backend .venv/bin/pytest backend/tests -q`

**Step 3: Run frontend checks**

Run:
- `npm --prefix frontend run test`
- `npm --prefix frontend run build`

**Step 4: Run live manual checks**

Run:
- llama smoke test
- one accepted sample through gateway
- one rejected real-irrelevant sample through gateway

**Step 5: Record result**
- If the irrelevant sample still returns `IN_SCOPE`, stop and report model-quality blocker explicitly.
