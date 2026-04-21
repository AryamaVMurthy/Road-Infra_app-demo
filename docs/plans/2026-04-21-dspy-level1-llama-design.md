# DSPy Level 1 Llama Runtime Design

**Goal:** Replace the current handwritten two-pass llama runtime with a single-pass multimodal request whose prompt is sourced from the saved DSPy Level 1 GEPA program.

## Decision

The live `llama-server` path will keep the current service architecture:

- `backend` calls `vlm-gateway`
- `vlm-gateway` queues work and calls `llama-server`
- `llama-server` performs one multimodal classification request per submission

The current handwritten prompt in `vlm_gateway/app/prompts.py` will no longer define the classification policy. Instead, the gateway will read the exact optimized Level 1 instructions from the saved DSPy GEPA program artifact and adapt only the output envelope to the live binary contract:

- `IN_SCOPE`
- `REJECTED`
- `category_name = null`

## Why

The existing two-pass runtime wastes latency by running:

1. description request
2. classification request

Live verification showed this path also produced an obvious false positive on an irrelevant cat image. The DSPy GEPA Level 1 artifact already contains a stricter and better-calibrated instruction set for the same accept/reject task. Reusing that exact artifact removes prompt drift between offline optimization and online serving.

## Implementation Shape

1. Add a small loader that reads the DSPy GEPA Level 1 compiled program and extracts:
   - the exact `instructions`
   - the input/output field prefixes if needed for formatting
2. Replace the handwritten runtime classification prompt builder with a DSPy-derived builder.
3. Remove the description pass from the llama runtime.
4. Keep the backend/gateway response contract unchanged.
5. Reduce latency by:
   - making a single model request instead of two
   - resizing images before upload to the model
   - tightening llama server runtime flags for CPU execution

## Constraints

- The serving path must remain Level 1 only.
- Backend API contract must not change.
- No silent fallback to handwritten prompts if DSPy prompt extraction fails; startup must fail explicitly.
- The runtime must use the saved DSPy program artifact as the source of truth.
