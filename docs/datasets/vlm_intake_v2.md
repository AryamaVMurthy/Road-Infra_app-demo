# VLM Intake v2 Benchmark Corpus

This is the only supported dataset-prep track in `.worktrees/with_AI_filtering`.

## Purpose

`vlm_intake_v2` is a benchmark and evaluation corpus for the local image-intake VLM. It is not the production taxonomy-aligned training set for the live app.

The dataset is explicitly structured around:

- accepted civic-issue samples
- rejected real-irrelevant samples
- rejected synthetic-spoof samples

Each manifest row carries both:

- `intake_outcome`
- `is_spoof`

So reject handling stays binary at the top level while preserving a clear spoof/not-spoof distinction for offline evaluation.

## Size and Split

- Total samples: `318`
- Accepted positives: `258`
- Rejected real-irrelevant: `24`
- Rejected synthetic-spoof: `36`

Accepted labels:

- `pothole`
- `damaged_road`
- `damaged_road_sign`
- `garbage_litter`

Split plan:

- `train`: `254`
- `test`: `64`

## Source Mix

Accepted positives:

- `Programmer-RD-AI/road-issues-detection-dataset`
- `manot/pothole-segmentation`
- `keremberke/pothole-segmentation`

Rejected real-irrelevant:

- `cvdl/oxford-pets`
- `keremberke/indoor-scene-classification`

Rejected synthetic-spoof:

- `Zitacron/real-vs-ai-corpus` filtered to `label_text=ai`, diversified by upstream `source_dataset`
- `prithivMLmods/Realistic-Face-Portrait-1024px`
- `absinc/sopg`

## Build Order

1. Fetch primary positives:

```bash
python tools/dataset_prep/fetch_positive_mirror.py \
  --config configs/datasets/vlm_intake_v2.yaml
```

2. Fetch pothole supplements:

```bash
python tools/dataset_prep/fetch_pothole_supplement.py \
  --config configs/datasets/vlm_intake_v2.yaml
```

3. Fetch rejected sources:

```bash
python tools/dataset_prep/fetch_hf_rejected_sources.py \
  --config configs/datasets/vlm_intake_v2.yaml
```

4. Build the normalized benchmark corpus:

```bash
python tools/dataset_prep/build_train_test.py \
  --config configs/datasets/vlm_intake_v2.yaml
```

5. Run live gateway evaluation on the held-out split:

```bash
python tools/dataset_prep/validate_dataset.py \
  --manifest artifacts/datasets/vlm_intake_v2/manifests/test.jsonl \
  --gateway-url http://localhost:8090 \
  --timeout-seconds 240 \
  --sleep-seconds 0.5
```

If the run is interrupted, rerun the same command. Predictions are cached to
`artifacts/datasets/vlm_intake_v2/reports/validation/predictions_cache.json`
and completed sample IDs are skipped on resume.

## Outputs

Generated under `artifacts/datasets/vlm_intake_v2/`:

- `raw/kaggle/road_issues_detection/`
- `raw/hf_supplements/`
- `raw/rejected_datasets/`
- `images/train/`
- `images/test/`
- `manifests/all_samples.jsonl`
- `manifests/train.jsonl`
- `manifests/test.jsonl`
- `manifests/label_map.json`
- `reports/source_inventory.csv`
- `reports/excluded_samples.csv`
- `reports/dedup_report.csv`
- `reports/dataset_summary.md`
- `reports/validation/`

## DSPy Two-Stage Export Contract

The `vlm_intake_v2` manifests are the single source of truth for DSPy intake
training exports. The exporter must fail fast if a manifest is missing,
malformed, or references an image path that does not exist on disk.

Expected JSONL exports:

- `dspy_exports/level1_train.jsonl`
- `dspy_exports/level1_test.jsonl`
- `dspy_exports/level2_train.jsonl`
- `dspy_exports/level2_test.jsonl`

Each exported row must preserve:

- `sample_id`
- `split` with the existing held-out names `train` and `test`
- `relative_image_path` copied directly from the manifest
- `subgroup` for subgroup-aware evaluation

Level 1 rows use only binary labels:

- `in_scope_category_image` for every accepted manifest record
- `spoof_or_out_of_scope` for every rejected manifest record

Level 1 subgroup values must distinguish:

- `accepted/<class>` for accepted examples, for example `accepted/pothole`
- `rejected_real_irrelevant`
- `rejected_synthetic_spoof`

Level 2 rows include only accepted examples and use the category label as the
`label` field. The only supported Level 2 labels are:

- `pothole`
- `damaged_road`
- `damaged_road_sign`
- `garbage_litter`

## Fail-Fast Rules

The pipeline errors explicitly when:

- a configured source directory is missing
- a source yields fewer images than configured
- an image is smaller than `min_short_edge`
- a sidecar is missing its paired image
- a split target exceeds the selected pool
- a manifest references a non-existent image

No stale `web_negatives`, no silent rebalancing, and no hidden fallback sources are allowed in `v2`.
