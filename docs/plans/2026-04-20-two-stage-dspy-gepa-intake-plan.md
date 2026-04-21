# Two-Stage DSPy GEPA Intake Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current single-stage intake classifier with a two-stage pipeline where Level 1 decides `spoof_or_out_of_scope` vs `in_scope_category_image`, and Level 2 assigns the exact category only for Level 1 accepts.

**Architecture:** Keep the current separate local VLM runtime and queued gateway, but move classification logic behind a DSPy program boundary. Train and optimize two distinct DSPy modules against the existing `vlm_intake_v2` benchmark corpus using GEPA as the primary prompt optimizer and an explicit comparison run with `MIPROv2` as a secondary baseline. Level 1 is intentionally biased toward `non-spoof` only when an image plausibly belongs to one of the accepted categories; every other image, including irrelevant real images and synthetic images, is treated as `spoof_or_out_of_scope`.

**Tech Stack:** DSPy, GEPA, MIPROv2, local OpenAI-compatible `llama-server`, existing `vlm_gateway`, existing `vlm_intake_v2` dataset, pytest.

---

## Current Baseline

Use the existing held-out benchmark at `artifacts/datasets/vlm_intake_v2/manifests/test.jsonl` as the baseline.

Current single-stage system metrics from `reports/validation/validation_summary.json`:

- overall accuracy: `0.4375`
- accept/reject accuracy: `0.5625`
- real-irrelevant reject rate: `1.0`
- synthetic-spoof reject rate: `1.0`
- accepted-class recall is poor outside potholes

Interpretation:

- the current prompt stack is too conservative
- it rejects irrelevant and synthetic images correctly
- it fails to preserve recall on valid in-category issue images

That is the exact failure mode this plan is addressing.

## Label Semantics

This plan uses the following internal semantics:

- Level 1 positive label: `in_scope_category_image`
- Level 1 negative label: `spoof_or_out_of_scope`
- Level 2 labels: exact accepted classes only

Important:

- `non-spoof` does **not** mean “real image”
- `non-spoof` means “image plausibly belongs to one of the accepted categories”
- any real but irrelevant image is intentionally grouped with synthetic images under the Level 1 negative label

This matches the requested operational behavior.

## Accepted Categories for This Phase

Use the current `v2` accepted labels exactly:

- `pothole`
- `damaged_road`
- `damaged_road_sign`
- `garbage_litter`

Do not expand taxonomy during this phase.

## Optimization Strategy

### Level 1

Optimize a DSPy module that takes:

- image
- active category catalog
- category guidance

and returns:

- `decision`: `IN_SCOPE` or `REJECT`
- optional `best_matching_category_hint`
- optional rationale text for optimizer feedback

GEPA should optimize the instruction text for this module using textual feedback that explicitly says:

- why an accepted image should have been considered in-scope
- which category makes it in-scope
- why an irrelevant or synthetic image should be rejected

The prompt must bias toward `IN_SCOPE` whenever any category plausibly matches.

### Level 2

Optimize a separate DSPy module that only sees examples already labeled `IN_SCOPE`.

It returns:

- `category_name`

Optimize this module for macro performance across the accepted classes, not raw accuracy dominated by potholes.

### Optimizer Policy

Primary optimizer:

- `dspy.GEPA`

Comparison baseline:

- `dspy.MIPROv2`

Selection rule:

- choose the optimizer that yields the best held-out two-stage end-to-end score on the `v2` test split
- do not silently switch optimizers without recording the comparison

## Metrics

### Level 1 tuning metric

Implement a weighted DSPy metric with feedback.

Scoring goals:

- maximize accepted recall
- preserve high reject precision for both real-irrelevant and synthetic-spoof
- avoid bias toward only one reject subtype

Metric shape:

- accepted sample, predicted `IN_SCOPE`: strong reward
- accepted sample, predicted `REJECT`: strong penalty
- real-irrelevant sample, predicted `REJECT`: reward
- synthetic-spoof sample, predicted `REJECT`: reward
- any negative sample, predicted `IN_SCOPE`: strong penalty

Add subgroup-aware checks:

- accepted recall
- real-irrelevant reject rate
- synthetic-spoof reject rate
- per-accepted-class in-scope recall

Feedback text requirements:

- if a valid issue was rejected, say which category made it in-scope
- if an irrelevant image was accepted, say which visible evidence shows it is outside all allowed categories
- if a synthetic image was accepted, say which synthetic cues or out-of-scope cues justify rejection

### Level 2 tuning metric

Use macro-averaged category correctness.

Scoring goals:

- exact category match
- stronger penalty for `garbage_litter`, `damaged_road`, and `damaged_road_sign` collapse into `pothole` or `damaged_road`

Feedback text requirements:

- explain why the gold category is correct using visible features
- explain why the predicted category is wrong

### End-to-end selection metric

Use a composite score on held-out test:

- 40% Level 1 accepted recall
- 20% Level 1 real-irrelevant reject rate
- 20% Level 1 synthetic-spoof reject rate
- 20% Level 2 macro category accuracy over accepted examples

Also track:

- full confusion matrix
- false reject count by accepted class
- false accept count by negative subgroup

## Data Plan

Use the current `vlm_intake_v2` benchmark corpus as the only data source for this phase.

### Level 1 train/dev/test views

Derive binary labels from the current manifests:

- accepted positives -> `in_scope_category_image`
- `rejected_real_irrelevant` -> `spoof_or_out_of_scope`
- `rejected_synthetic_spoof` -> `spoof_or_out_of_scope`

Keep subgroup metadata for evaluation:

- `accepted/<class>`
- `rejected_real_irrelevant`
- `rejected_synthetic_spoof`

### Level 2 train/dev/test views

Filter to accepted examples only:

- `pothole`
- `damaged_road`
- `damaged_road_sign`
- `garbage_litter`

### Data hygiene rules

- no relabeling without explicit manifest updates
- no silent resampling
- no synthetic augmentation in this phase
- preserve the existing held-out `test.jsonl` as the immutable evaluation split

## DSPy Program Design

### Level 1 signature

Create a signature similar to:

```python
class InScopeGate(dspy.Signature):
    image: dspy.Image = dspy.InputField()
    category_catalog: str = dspy.InputField()
    decision: Literal["IN_SCOPE", "REJECT"] = dspy.OutputField()
    best_matching_category_hint: str | None = dspy.OutputField()
    rationale: str = dspy.OutputField()
```

### Level 2 signature

Create a signature similar to:

```python
class IssueCategoryClassifier(dspy.Signature):
    image: dspy.Image = dspy.InputField()
    category_catalog: str = dspy.InputField()
    category_name: Literal["pothole", "damaged_road", "damaged_road_sign", "garbage_litter"] = dspy.OutputField()
    rationale: str = dspy.OutputField()
```

### Two-stage orchestrator

Create a DSPy module that:

1. runs Level 1
2. if Level 1 returns `REJECT`, emits final `REJECTED`
3. if Level 1 returns `IN_SCOPE`, runs Level 2
4. returns final `ACCEPTED_CATEGORY_MATCH` plus `category_name`

Use this orchestrator for end-to-end evaluation, but optimize Level 1 and Level 2 separately first.

## Repository Changes

### Create DSPy training/optimization tooling

**Files:**
- Create: `tools/dspy_intake/common.py`
- Create: `tools/dspy_intake/signatures.py`
- Create: `tools/dspy_intake/programs.py`
- Create: `tools/dspy_intake/metrics.py`
- Create: `tools/dspy_intake/export_datasets.py`
- Create: `tools/dspy_intake/train_level1_gepa.py`
- Create: `tools/dspy_intake/train_level2_gepa.py`
- Create: `tools/dspy_intake/train_level1_mipro.py`
- Create: `tools/dspy_intake/train_level2_mipro.py`
- Create: `tools/dspy_intake/evaluate_two_stage.py`

### Persist compiled artifacts

**Files:**
- Create: `artifacts/models/intake_dspy/level1/`
- Create: `artifacts/models/intake_dspy/level2/`
- Create: `artifacts/models/intake_dspy/reports/`

Persist:

- GEPA-compiled Level 1 program
- GEPA-compiled Level 2 program
- MIPROv2 comparison outputs
- final selection report

### Gateway integration path

Do not replace the current prompt path immediately.

Add a separate explicit inference path first:

**Files:**
- Create: `vlm_gateway/app/dspy_pipeline.py`
- Modify: `vlm_gateway/app/server.py`
- Modify: `vlm_gateway/app/main.py`
- Modify: `vlm_gateway/app/schemas.py`

Requirements:

- allow explicit model strategy selection via env var, e.g. `VLM_PIPELINE_MODE=legacy_prompt|dspy_two_stage`
- no silent fallback from DSPy path to legacy prompt path
- if DSPy artifacts are missing, fail startup with explicit error

## Testing Plan

### Dataset export tests

**Files:**
- Create: `backend/tests/test_dspy_dataset_export.py`

Verify:

- Level 1 exported labels are binary and correct
- Level 2 export contains accepted examples only
- subgroup metadata is preserved
- held-out split remains unchanged

### Metric tests

**Files:**
- Create: `backend/tests/test_dspy_metrics.py`

Verify:

- false reject on accepted image scores worse than correct accept
- false accept on real-irrelevant scores worse than correct reject
- false accept on synthetic-spoof scores worse than correct reject
- feedback strings mention category or out-of-scope reasoning

### Program integration tests

**Files:**
- Create: `backend/tests/test_dspy_two_stage_program.py`

Verify:

- Level 1 reject short-circuits Level 2
- Level 1 accept runs Level 2
- orchestrator returns the existing gateway response contract shape

### Gateway tests

**Files:**
- Modify: `vlm_gateway/tests/test_queue_flow.py`
- Modify: `vlm_gateway/tests/test_live_gateway_contract.py`
- Create: `vlm_gateway/tests/test_dspy_pipeline_contract.py`

Verify:

- DSPy path returns `REJECTED` or `ACCEPTED_CATEGORY_MATCH`
- missing compiled artifacts fail explicitly
- pipeline mode selection is explicit

## Step-by-Step Task Plan

### Task 1: Freeze the problem contract

**Files:**
- Create: `docs/plans/2026-04-20-two-stage-dspy-gepa-intake-plan.md`
- Modify: `docs/datasets/vlm_intake_v2.md`

**Step 1: Write the failing documentation/tests**

- Add a test that asserts Level 1 exported labels only have `in_scope_category_image` and `spoof_or_out_of_scope`.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=backend ../../.venv/bin/pytest backend/tests/test_dspy_dataset_export.py -q
```

Expected:

- fail because export tooling does not exist yet

**Step 3: Write minimal export contract**

- document the two-stage label semantics in `docs/datasets/vlm_intake_v2.md`

**Step 4: Re-run tests**

- export tests should still fail until tooling exists

### Task 2: Export Level 1 and Level 2 DSPy datasets

**Files:**
- Create: `tools/dspy_intake/export_datasets.py`
- Test: `backend/tests/test_dspy_dataset_export.py`

**Step 1: Write failing tests**

Test:

- Level 1 export creates binary labels and subgroup tags
- Level 2 export creates category-only examples

**Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=backend ../../.venv/bin/pytest backend/tests/test_dspy_dataset_export.py -q
```

**Step 3: Implement minimal exporter**

- read `train.jsonl` and `test.jsonl`
- emit DSPy-friendly JSONL or pickle payloads
- preserve image paths and subgroup metadata

**Step 4: Re-run tests**

Expected:

- pass

### Task 3: Implement Level 1 DSPy program and metric

**Files:**
- Create: `tools/dspy_intake/signatures.py`
- Create: `tools/dspy_intake/programs.py`
- Create: `tools/dspy_intake/metrics.py`
- Test: `backend/tests/test_dspy_metrics.py`
- Test: `backend/tests/test_dspy_two_stage_program.py`

**Step 1: Write failing tests**

Test:

- Level 1 output parses as `IN_SCOPE` or `REJECT`
- metric penalizes false rejects heavily
- metric feedback explicitly references category fit or out-of-scope status

**Step 2: Run tests to verify failure**

**Step 3: Implement minimal Level 1 DSPy module**

- use `dspy.Image`
- include category catalog in the signature inputs
- return structured decision and rationale

**Step 4: Re-run tests**

### Task 4: Implement Level 2 DSPy program and metric

**Files:**
- Modify: `tools/dspy_intake/signatures.py`
- Modify: `tools/dspy_intake/programs.py`
- Modify: `tools/dspy_intake/metrics.py`
- Test: `backend/tests/test_dspy_metrics.py`
- Test: `backend/tests/test_dspy_two_stage_program.py`

**Step 1: Write failing tests**

Test:

- Level 2 only accepts valid category names
- macro-aware metric penalizes pothole collapse

**Step 2: Run tests to verify failure**

**Step 3: Implement minimal Level 2 module**

**Step 4: Re-run tests**

### Task 5: Build GEPA training harnesses

**Files:**
- Create: `tools/dspy_intake/train_level1_gepa.py`
- Create: `tools/dspy_intake/train_level2_gepa.py`

**Step 1: Write failing tests**

- harness loads train/dev sets
- GEPA compile call is wired with metric and reflection LM

**Step 2: Run tests to verify failure**

**Step 3: Implement minimal harness**

Requirements:

- connect DSPy to local OpenAI-compatible `llama-server`
- use explicit `reflection_lm`
- save compiled program artifacts
- save compile stats

**Step 4: Re-run tests**

### Task 6: Build MIPROv2 comparison harnesses

**Files:**
- Create: `tools/dspy_intake/train_level1_mipro.py`
- Create: `tools/dspy_intake/train_level2_mipro.py`

**Step 1: Write failing tests**

- harness runs compile and saves comparison artifacts

**Step 2: Run tests to verify failure**

**Step 3: Implement minimal harness**

**Step 4: Re-run tests**

### Task 7: Evaluate Level 1, Level 2, and end-to-end two-stage performance

**Files:**
- Create: `tools/dspy_intake/evaluate_two_stage.py`

**Step 1: Write failing tests**

- evaluation emits:
  - Level 1 subgroup metrics
  - Level 2 macro category metrics
  - end-to-end confusion matrix

**Step 2: Run tests to verify failure**

**Step 3: Implement evaluator**

- run held-out `test.jsonl`
- compare GEPA vs MIPROv2
- save report to `artifacts/models/intake_dspy/reports/`

**Step 4: Re-run tests**

### Task 8: Integrate selected two-stage program into the gateway

**Files:**
- Create: `vlm_gateway/app/dspy_pipeline.py`
- Modify: `vlm_gateway/app/server.py`
- Modify: `vlm_gateway/app/main.py`
- Modify: `vlm_gateway/app/schemas.py`
- Test: `vlm_gateway/tests/test_dspy_pipeline_contract.py`

**Step 1: Write failing tests**

- DSPy pipeline returns the existing gateway contract
- startup fails when artifacts are missing
- explicit mode selection works

**Step 2: Run tests to verify failure**

**Step 3: Implement minimal integration**

**Step 4: Re-run tests**

### Task 9: Run full repo verification plus benchmark report

**Files:**
- Modify: `docs/datasets/vlm_intake_v2.md`
- Create: `artifacts/models/intake_dspy/reports/final_selection_report.md`

**Step 1: Run full verification**

```bash
PYTHONPATH=backend ../../.venv/bin/pytest backend/tests -q
../../.venv/bin/pytest vlm_gateway/tests -q
```

**Step 2: Run held-out benchmark**

- Level 1 GEPA
- Level 2 GEPA
- Level 1 MIPROv2
- Level 2 MIPROv2
- end-to-end selected run

**Step 3: Save results**

Report must include:

- baseline current prompt-stack metrics
- Level 1 GEPA metrics
- Level 2 GEPA metrics
- MIPROv2 comparison metrics
- final selected two-stage system metrics
- subgroup analysis showing:
  - accepted recall
  - real-irrelevant reject rate
  - synthetic-spoof reject rate
  - per-class category recall

## Success Criteria

The plan is successful when all of the following are true:

- Level 1 no longer treats “real but irrelevant” as a special non-spoof case
- Level 1 only accepts images that plausibly belong to the accepted category catalog
- Level 1 subgroup evaluation shows no synthetic-only bias
- Level 2 category assignment materially improves macro accepted-class performance
- end-to-end held-out results exceed the current baseline on:
  - accepted recall
  - overall accuracy
  - macro category performance
- gateway can run the selected two-stage program without silent fallbacks

## External References

- DSPy official docs: https://dspy.ai/
- DSPy GEPA overview: https://dspy.ai/api/optimizers/GEPA/overview
- DSPy optimizer docs: https://github.com/stanfordnlp/dspy/blob/main/docs/docs/learn/optimization/optimizers.md
- GEPA repository: https://github.com/CerebrasResearch/gepa
