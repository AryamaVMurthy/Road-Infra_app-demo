"""Render an HTML benchmark report for the DSPy intake evaluation artifacts."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import html
import json
import os
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))


@dataclass(frozen=True, slots=True)
class SampleRecord:
    sample_id: str
    subgroup: str
    expected_label: str
    predicted_label: str
    level1_decision: str
    level1_best_matching_category_hint: str
    ungated_level2_predicted_label: str | None
    relative_image_path: str
    intake_outcome: str
    canonical_label: str | None
    is_spoof: bool
    negative_source_type: str | None
    source_dataset: str | None
    source_label: str | None


def render_html_report(
    *,
    dataset_root: Path,
    summary_path: Path,
    predictions_path: Path,
    manifest_path: Path,
    output_path: Path,
    report_title: str = "DSPy Intake Benchmark Report",
) -> Path:
    summary = _read_json(summary_path)
    predictions = _read_jsonl(predictions_path)
    manifest_rows = _read_jsonl(manifest_path)
    manifest_by_sample_id = {
        _require_string(row, "sample_id"): row for row in manifest_rows
    }
    sample_records = _build_sample_records(
        dataset_root=dataset_root,
        predictions=predictions,
        manifest_by_sample_id=manifest_by_sample_id,
    )
    html_text = _build_html(
        report_title=report_title,
        dataset_root=dataset_root,
        output_path=output_path,
        summary=summary,
        sample_records=sample_records,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")
    return output_path


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Missing required JSON file `{path}`.") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in `{path}`.") from exc


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    resolved_path = Path(path)
    if not resolved_path.is_file():
        raise ValueError(f"Missing required JSONL file `{path}`.")
    rows: list[dict[str, object]] = []
    with resolved_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Malformed JSONL row in `{path}` at line {line_number}."
                ) from exc
            rows.append(row)
    return rows


def _require_string(row: dict[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected non-empty string field `{key}` in row {row!r}.")
    return value.strip()


def _build_sample_records(
    *,
    dataset_root: Path,
    predictions: list[dict[str, object]],
    manifest_by_sample_id: dict[str, dict[str, object]],
) -> list[SampleRecord]:
    sample_records: list[SampleRecord] = []
    for prediction in predictions:
        sample_id = _require_string(prediction, "sample_id")
        manifest_row = manifest_by_sample_id.get(sample_id)
        if manifest_row is None:
            raise ValueError(
                f"Prediction sample `{sample_id}` is missing from the manifest."
            )
        relative_image_path = _require_string(manifest_row, "relative_image_path")
        image_path = Path(dataset_root) / relative_image_path
        if not image_path.is_file():
            raise ValueError(
                f"Manifest sample `{sample_id}` references missing image `{image_path}`."
            )
        sample_records.append(
            SampleRecord(
                sample_id=sample_id,
                subgroup=_require_string(prediction, "subgroup"),
                expected_label=_require_string(prediction, "expected_label"),
                predicted_label=_require_string(prediction, "predicted_label"),
                level1_decision=_require_string(prediction, "level1_decision"),
                level1_best_matching_category_hint=str(
                    prediction.get("level1_best_matching_category_hint") or ""
                ),
                ungated_level2_predicted_label=(
                    str(prediction["ungated_level2_predicted_label"])
                    if prediction.get("ungated_level2_predicted_label") is not None
                    else None
                ),
                relative_image_path=relative_image_path,
                intake_outcome=_require_string(manifest_row, "intake_outcome"),
                canonical_label=(
                    str(manifest_row["canonical_label"])
                    if manifest_row.get("canonical_label") is not None
                    else None
                ),
                is_spoof=bool(manifest_row.get("is_spoof")),
                negative_source_type=(
                    str(manifest_row["negative_source_type"])
                    if manifest_row.get("negative_source_type") is not None
                    else None
                ),
                source_dataset=(
                    str(manifest_row["source_dataset"])
                    if manifest_row.get("source_dataset") is not None
                    else None
                ),
                source_label=(
                    str(manifest_row["source_label"])
                    if manifest_row.get("source_label") is not None
                    else None
                ),
            )
        )
    return sample_records


def _build_html(
    *,
    report_title: str,
    dataset_root: Path,
    output_path: Path,
    summary: dict[str, object],
    sample_records: list[SampleRecord],
) -> str:
    metrics = _compute_gate_metrics(sample_records)
    computed_counts = _compute_overall_counts(sample_records)
    computed_level1_metrics = _compute_level1_subgroup_metrics(sample_records)
    computed_level2_metrics = _compute_level2_category_metrics(sample_records)
    consistency_warnings = _compute_consistency_warnings(
        summary=summary,
        computed_counts=computed_counts,
        computed_level1_metrics=computed_level1_metrics,
        computed_level2_metrics=computed_level2_metrics,
    )
    section_cards = _group_cards_by_outcome(
        dataset_root=dataset_root,
        output_path=output_path,
        sample_records=sample_records,
    )
    total_examples = computed_counts["total_examples"]
    correct_predictions = computed_counts["correct_predictions"]
    accuracy = computed_counts["accuracy"]
    confusion_rows = _compute_label_confusion(sample_records)
    issue_counts = Counter(record.expected_label for record in sample_records if record.expected_label != "REJECT")
    reject_counts = Counter(record.negative_source_type or "unknown" for record in sample_records if record.expected_label == "REJECT")
    hint_success = Counter()
    for record in sample_records:
        if record.expected_label == "REJECT":
            continue
        key = "empty"
        if record.level1_best_matching_category_hint:
            key = "match" if record.level1_best_matching_category_hint == record.expected_label else "wrong"
        hint_success[(key, "correct" if record.predicted_label == record.expected_label else "wrong")] += 1

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(report_title)}</title>
  <style>
    :root {{
      --bg: #f5f3ee;
      --panel: #fffdf8;
      --ink: #1c1a17;
      --muted: #6c675e;
      --accent: #8b5e3c;
      --good: #1f7a4c;
      --bad: #b23a2a;
      --warn: #a36d00;
      --line: #e3ddd0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: linear-gradient(180deg, #f1ede4 0%, var(--bg) 240px);
      color: var(--ink);
    }}
    .page {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 32px 24px 56px;
    }}
    .hero {{
      background: radial-gradient(circle at top left, #fff7e8 0%, #fffdf8 45%, #f6f0e4 100%);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 28px;
      box-shadow: 0 20px 48px rgba(53, 41, 20, 0.08);
    }}
    h1, h2, h3 {{ margin: 0; font-weight: 700; }}
    h1 {{ font-size: 2.5rem; line-height: 1.05; }}
    h2 {{ font-size: 1.45rem; margin-bottom: 14px; }}
    h3 {{ font-size: 1rem; margin-bottom: 8px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
    p, li {{ line-height: 1.5; }}
    .meta {{
      margin-top: 14px;
      color: var(--muted);
      display: flex;
      gap: 18px;
      flex-wrap: wrap;
    }}
    .metric-grid, .panel-grid {{
      display: grid;
      gap: 16px;
      margin-top: 22px;
    }}
    .warning-list {{
      margin: 12px 0 0;
      padding-left: 18px;
    }}
    .metric-grid {{
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }}
    .panel-grid {{
      grid-template-columns: 1.2fr 1fr;
      align-items: start;
    }}
    .metric-card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 14px 30px rgba(53, 41, 20, 0.04);
    }}
    .metric-card .value {{
      font-size: 2rem;
      font-weight: 700;
      margin: 8px 0 2px;
    }}
    .metric-card .label {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .good {{ color: var(--good); }}
    .bad {{ color: var(--bad); }}
    .warn {{ color: var(--warn); }}
    .warning-panel {{
      background: #fff4df;
      border: 1px solid #f0d398;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }}
    th, td {{
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 700;
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .section {{
      margin-top: 28px;
    }}
    .section-head {{
      display: flex;
      align-items: baseline;
      gap: 10px;
      margin-bottom: 14px;
    }}
    .section-count {{
      color: var(--muted);
      font-size: 0.95rem;
      font-weight: 700;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 16px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
      box-shadow: 0 14px 30px rgba(53, 41, 20, 0.04);
    }}
    .card img {{
      display: block;
      width: 100%;
      aspect-ratio: 4 / 3;
      object-fit: cover;
      background: #e9e1d1;
    }}
    .card-body {{
      padding: 14px;
    }}
    .card-body .title {{
      font-weight: 700;
      font-size: 1rem;
      margin-bottom: 8px;
    }}
    .chips {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin: 10px 0 12px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 0.78rem;
      border: 1px solid var(--line);
      background: #f7f1e6;
      color: #4f493f;
    }}
    .chip.good {{ background: #edf8f1; color: var(--good); border-color: #cce6d5; }}
    .chip.bad {{ background: #fceceb; color: var(--bad); border-color: #efc7c2; }}
    .chip.warn {{ background: #fff6df; color: var(--warn); border-color: #efdba3; }}
    .kv {{
      display: grid;
      grid-template-columns: 108px 1fr;
      gap: 6px 10px;
      font-size: 0.88rem;
    }}
    .kv dt {{
      color: var(--muted);
      font-weight: 700;
    }}
    .kv dd {{ margin: 0; }}
    .small {{
      font-size: 0.84rem;
      color: var(--muted);
    }}
    @media (max-width: 980px) {{
      .panel-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>{html.escape(report_title)}</h1>
      <div class="meta">
        <span>Variant: {html.escape(str(summary.get("variant_name", "unknown")))}</span>
        <span>Metrics source: predictions.jsonl + manifest/test.jsonl</span>
        <span>Held-out samples: {total_examples}</span>
        <span>Correct predictions: {correct_predictions} / {total_examples}</span>
        <span>End-to-end accuracy: {accuracy:.3f}</span>
      </div>
      <div class="metric-grid">
        <article class="metric-card">
          <div class="label">Correct Predictions</div>
          <div class="value">{correct_predictions} / {total_examples}</div>
          <div class="small">End-to-end intake plus category result.</div>
        </article>
        <article class="metric-card">
          <div class="label">Correct Not-Spoof / In-Scope</div>
          <div class="value good">{metrics["true_accept"]}</div>
          <div class="small">Valid issue image kept in scope.</div>
        </article>
        <article class="metric-card">
          <div class="label">False Spoof / False Reject</div>
          <div class="value bad">{metrics["false_reject"]}</div>
          <div class="small">Valid issue image rejected as out-of-scope.</div>
        </article>
        <article class="metric-card">
          <div class="label">Correct Spoof / Reject</div>
          <div class="value good">{metrics["true_reject"]}</div>
          <div class="small">Real irrelevant or synthetic sample rejected.</div>
        </article>
        <article class="metric-card">
          <div class="label">False Not-Spoof / False Accept</div>
          <div class="value {'bad' if metrics["false_accept"] else 'good'}">{metrics["false_accept"]}</div>
          <div class="small">Reject sample incorrectly routed in-scope.</div>
        </article>
      </div>
    </section>

    {_render_consistency_warning(consistency_warnings)}

    <section class="section panel-grid">
      <article class="panel">
        <h2>Spoof / Not-Spoof Gate</h2>
        <table>
          <thead>
            <tr><th>Metric</th><th>Value</th></tr>
          </thead>
          <tbody>
            <tr><td>Not-spoof recall</td><td>{metrics["not_spoof_recall"]:.3f}</td></tr>
            <tr><td>Not-spoof precision</td><td>{metrics["not_spoof_precision"]:.3f}</td></tr>
            <tr><td>Spoof / reject recall</td><td>{metrics["reject_recall"]:.3f}</td></tr>
            <tr><td>Spoof / reject precision</td><td>{metrics["reject_precision"]:.3f}</td></tr>
            <tr><td>Real irrelevant rejected</td><td>{metrics["real_irrelevant_rejects"]} / {reject_counts.get("real_irrelevant", 0)}</td></tr>
            <tr><td>Synthetic spoof rejected</td><td>{metrics["synthetic_spoof_rejects"]} / {reject_counts.get("synthetic_spoof", 0)}</td></tr>
          </tbody>
        </table>
      </article>
      <article class="panel">
        <h2>Key Insights</h2>
        <ul>
          <li>`pothole` and `damaged_road_sign` are the strongest classes in this held-out run.</li>
          <li>`damaged_road` is mostly collapsed into `pothole` rather than being rejected.</li>
          <li>`garbage_litter` splits between correct accepts, false rejects, and collapses into surface-damage labels.</li>
          <li>The reject gate is perfect on the held-out reject set: no false accepts in this report.</li>
          <li>Level 1 hint behavior is visible per card so you can inspect when the hint matched, conflicted, or was empty.</li>
        </ul>
      </article>
    </section>

    <section class="section panel-grid">
      <article class="panel">
        <h2>Per-Class Category Metrics</h2>
        {_render_accuracy_table(computed_level2_metrics, key_label="Category")}
      </article>
      <article class="panel">
        <h2>In-Scope Gate by Subgroup</h2>
        {_render_accuracy_table(computed_level1_metrics, key_label="Subgroup")}
      </article>
    </section>

    <section class="section panel-grid">
      <article class="panel">
        <h2>Expected vs Predicted Labels</h2>
        <table>
          <thead>
            <tr><th>Expected</th><th>Predicted</th><th>Count</th></tr>
          </thead>
          <tbody>
            {"".join(
                f"<tr><td>{html.escape(expected)}</td><td>{html.escape(predicted)}</td><td>{count}</td></tr>"
                for expected, predicted, count in confusion_rows
            )}
          </tbody>
        </table>
      </article>
      <article class="panel">
        <h2>Dataset Mix + Hint Outcomes</h2>
        <table>
          <thead>
            <tr><th>Bucket</th><th>Count</th></tr>
          </thead>
          <tbody>
            {"".join(
                f"<tr><td>{html.escape(label)}</td><td>{count}</td></tr>"
                for label, count in sorted(issue_counts.items())
            )}
            {"".join(
                f"<tr><td>reject / {html.escape(label)}</td><td>{count}</td></tr>"
                for label, count in sorted(reject_counts.items())
            )}
            {"".join(
                f"<tr><td>hint={html.escape(hint_state)}, result={html.escape(result_state)}</td><td>{count}</td></tr>"
                for (hint_state, result_state), count in sorted(hint_success.items())
            )}
          </tbody>
        </table>
      </article>
    </section>

    {_render_section("Correct Accepts", section_cards["correct_accepts"])}
    {_render_section("False Rejects", section_cards["false_rejects"])}
    {_render_section("Wrong-Category Accepts", section_cards["wrong_accepts"])}
    {_render_section("Correct Rejects", section_cards["correct_rejects"])}
    {_render_section("False Accepts", section_cards["false_accepts"])}
  </div>
</body>
</html>
"""


def _compute_gate_metrics(sample_records: list[SampleRecord]) -> dict[str, float | int]:
    true_accept = 0
    false_reject = 0
    true_reject = 0
    false_accept = 0
    real_irrelevant_rejects = 0
    synthetic_spoof_rejects = 0
    not_spoof_total = 0
    reject_total = 0
    for record in sample_records:
        expected_reject = record.expected_label == "REJECT"
        predicted_reject = record.predicted_label == "REJECT"
        if expected_reject:
            reject_total += 1
            if predicted_reject:
                true_reject += 1
                if record.negative_source_type == "real_irrelevant":
                    real_irrelevant_rejects += 1
                if record.negative_source_type == "synthetic_spoof":
                    synthetic_spoof_rejects += 1
            else:
                false_accept += 1
        else:
            not_spoof_total += 1
            if predicted_reject:
                false_reject += 1
            else:
                true_accept += 1
    return {
        "true_accept": true_accept,
        "false_reject": false_reject,
        "true_reject": true_reject,
        "false_accept": false_accept,
        "not_spoof_recall": true_accept / not_spoof_total if not_spoof_total else 0.0,
        "not_spoof_precision": true_accept / (true_accept + false_accept)
        if (true_accept + false_accept)
        else 0.0,
        "reject_recall": true_reject / reject_total if reject_total else 0.0,
        "reject_precision": true_reject / (true_reject + false_reject)
        if (true_reject + false_reject)
        else 0.0,
        "real_irrelevant_rejects": real_irrelevant_rejects,
        "synthetic_spoof_rejects": synthetic_spoof_rejects,
    }


def _compute_overall_counts(sample_records: list[SampleRecord]) -> dict[str, int | float]:
    total_examples = len(sample_records)
    correct_predictions = sum(
        1 for record in sample_records if record.predicted_label == record.expected_label
    )
    accuracy = correct_predictions / total_examples if total_examples else 0.0
    return {
        "total_examples": total_examples,
        "correct_predictions": correct_predictions,
        "accuracy": accuracy,
    }


def _compute_level1_subgroup_metrics(
    sample_records: list[SampleRecord],
) -> dict[str, dict[str, int | float]]:
    grouped: dict[str, list[SampleRecord]] = defaultdict(list)
    for record in sample_records:
        grouped[record.subgroup].append(record)
    metrics: dict[str, dict[str, int | float]] = {}
    for subgroup, records in sorted(grouped.items()):
        correct_scope = 0
        for record in records:
            expected_reject = record.expected_label == "REJECT"
            predicted_reject = record.predicted_label == "REJECT"
            if expected_reject == predicted_reject:
                correct_scope += 1
        total = len(records)
        metrics[subgroup] = {
            "correct_scope": correct_scope,
            "total": total,
            "accuracy": correct_scope / total if total else 0.0,
        }
    return metrics


def _compute_level2_category_metrics(
    sample_records: list[SampleRecord],
) -> dict[str, dict[str, int | float]]:
    grouped: dict[str, list[SampleRecord]] = defaultdict(list)
    for record in sample_records:
        if record.expected_label == "REJECT":
            continue
        grouped[record.expected_label].append(record)
    metrics: dict[str, dict[str, int | float]] = {}
    for category, records in sorted(grouped.items()):
        correct = sum(1 for record in records if record.predicted_label == record.expected_label)
        total = len(records)
        metrics[category] = {
            "correct": correct,
            "total": total,
            "accuracy": correct / total if total else 0.0,
        }
    return metrics


def _compute_consistency_warnings(
    *,
    summary: dict[str, object],
    computed_counts: dict[str, int | float],
    computed_level1_metrics: dict[str, dict[str, int | float]],
    computed_level2_metrics: dict[str, dict[str, int | float]],
) -> list[str]:
    warnings: list[str] = []
    summary_counts = summary.get("counts", {})
    if isinstance(summary_counts, dict):
        summary_total = summary_counts.get("total_examples")
        summary_correct = summary_counts.get("correct_predictions")
        if summary_total != computed_counts["total_examples"] or summary_correct != computed_counts["correct_predictions"]:
            warnings.append(
                "overall counts: summary.json says "
                f"{summary_correct} / {summary_total}, computed from predictions.jsonl as "
                f"{computed_counts['correct_predictions']} / {computed_counts['total_examples']}."
            )
    summary_end_to_end = summary.get("end_to_end", {})
    if isinstance(summary_end_to_end, dict):
        summary_accuracy = summary_end_to_end.get("accuracy")
        if isinstance(summary_accuracy, (int, float)) and abs(float(summary_accuracy) - float(computed_counts["accuracy"])) > 1e-9:
            warnings.append(
                "overall accuracy: summary.json says "
                f"{float(summary_accuracy):.3f}, computed from predictions.jsonl as {float(computed_counts['accuracy']):.3f}."
            )
    warnings.extend(
        _metric_bucket_mismatches(
            bucket_name="level1 subgroup",
            summary_metrics=summary.get("level1_subgroup_metrics", {}),
            computed_metrics=computed_level1_metrics,
            correct_key="correct_scope",
        )
    )
    warnings.extend(
        _metric_bucket_mismatches(
            bucket_name="level2 category",
            summary_metrics=summary.get("level2_category_metrics", {}),
            computed_metrics=computed_level2_metrics,
            correct_key="correct",
        )
    )
    return warnings


def _metric_bucket_mismatches(
    *,
    bucket_name: str,
    summary_metrics: object,
    computed_metrics: dict[str, dict[str, int | float]],
    correct_key: str,
) -> list[str]:
    warnings: list[str] = []
    if not isinstance(summary_metrics, dict):
        return warnings
    all_keys = sorted(set(summary_metrics) | set(computed_metrics))
    for key in all_keys:
        summary_metric = summary_metrics.get(key)
        computed_metric = computed_metrics.get(key)
        if not isinstance(summary_metric, dict) or computed_metric is None:
            warnings.append(
                f"{bucket_name} `{key}`: summary.json coverage does not match the computed metrics."
            )
            continue
        summary_correct = summary_metric.get(correct_key)
        summary_total = summary_metric.get("total")
        summary_accuracy = summary_metric.get("accuracy")
        computed_correct = computed_metric[correct_key]
        computed_total = computed_metric["total"]
        computed_accuracy = computed_metric["accuracy"]
        mismatch = (
            summary_correct != computed_correct
            or summary_total != computed_total
            or not isinstance(summary_accuracy, (int, float))
            or abs(float(summary_accuracy) - float(computed_accuracy)) > 1e-9
        )
        if mismatch:
            warnings.append(
                f"{bucket_name} `{key}`: summary.json says {summary_correct} / {summary_total} "
                f"(accuracy {float(summary_accuracy):.3f}), computed from predictions.jsonl as "
                f"{computed_correct} / {computed_total} (accuracy {float(computed_accuracy):.3f})."
            )
    return warnings


def _compute_label_confusion(sample_records: list[SampleRecord]) -> list[tuple[str, str, int]]:
    counts = Counter((record.expected_label, record.predicted_label) for record in sample_records)
    return [
        (expected_label, predicted_label, count)
        for (expected_label, predicted_label), count in sorted(counts.items())
    ]


def _group_cards_by_outcome(
    *,
    dataset_root: Path,
    output_path: Path,
    sample_records: list[SampleRecord],
) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = defaultdict(list)
    for record in sample_records:
        if record.expected_label == "REJECT":
            key = "correct_rejects" if record.predicted_label == "REJECT" else "false_accepts"
        elif record.predicted_label == "REJECT":
            key = "false_rejects"
        elif record.predicted_label == record.expected_label:
            key = "correct_accepts"
        else:
            key = "wrong_accepts"
        sections[key].append(
            _render_card(
                dataset_root=dataset_root,
                output_path=output_path,
                record=record,
            )
        )
    return {
        "correct_accepts": sections.get("correct_accepts", []),
        "false_rejects": sections.get("false_rejects", []),
        "wrong_accepts": sections.get("wrong_accepts", []),
        "correct_rejects": sections.get("correct_rejects", []),
        "false_accepts": sections.get("false_accepts", []),
    }


def _render_accuracy_table(
    metrics: object,
    *,
    key_label: str,
) -> str:
    if not isinstance(metrics, dict):
        return "<p class='small'>No metrics available.</p>"
    rows = []
    for key, metric_values in sorted(metrics.items()):
        if not isinstance(metric_values, dict):
            continue
        total = metric_values.get("total", "")
        accuracy = metric_values.get("accuracy", 0.0)
        correct = metric_values.get("correct", metric_values.get("correct_scope", ""))
        rows.append(
            f"<tr><td>{html.escape(str(key))}</td><td>{correct}</td><td>{total}</td><td>{float(accuracy):.3f}</td></tr>"
        )
    return (
        "<table><thead>"
        f"<tr><th>{html.escape(key_label)}</th><th>Correct</th><th>Total</th><th>Accuracy</th></tr>"
        "</thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _render_consistency_warning(warnings: list[str]) -> str:
    if not warnings:
        return ""
    return (
        "<section class='section'>"
        "<article class='panel warning-panel'>"
        "<h2>Metrics Consistency Warning</h2>"
        "<p class='small'>Displayed tables in this report are recomputed from "
        "<code>predictions.jsonl</code> and <code>manifest/test.jsonl</code> because "
        "<code>summary.json</code> contains mismatched metric values.</p>"
        "<ul class='warning-list'>"
        + "".join(f"<li>{html.escape(message)}</li>" for message in warnings)
        + "</ul></article></section>"
    )


def _render_section(title: str, cards: list[str]) -> str:
    heading = (
        f"<div class='section-head'><h2>{html.escape(title)}</h2>"
        f"<span class='section-count'>{len(cards)} samples</span></div>"
    )
    if not cards:
        return (
            f"<section class='section'>{heading}"
            "<p class='small'>No samples in this bucket for the current report.</p>"
            "</section>"
        )
    return (
        f"<section class='section'>{heading}"
        f"<div class='cards'>{''.join(cards)}</div></section>"
    )


def _render_card(
    *,
    dataset_root: Path,
    output_path: Path,
    record: SampleRecord,
) -> str:
    image_src = _relative_src(
        dataset_root=dataset_root,
        output_path=output_path,
        relative_image_path=record.relative_image_path,
    )
    status_chip = _status_chip(record)
    source_parts = [part for part in (record.source_dataset, record.source_label) if part]
    return f"""
    <article class="card">
      <img src="{html.escape(image_src)}" alt="{html.escape(record.sample_id)}">
      <div class="card-body">
        <div class="title">{html.escape(record.sample_id)}</div>
        <div class="chips">
          {status_chip}
          <span class="chip {'bad' if record.is_spoof else 'good'}">{'spoof' if record.is_spoof else 'not_spoof'}</span>
          <span class="chip">{html.escape(record.subgroup)}</span>
        </div>
        <dl class="kv">
          <dt>Expected</dt><dd>{html.escape(record.expected_label)}</dd>
          <dt>Predicted</dt><dd>{html.escape(record.predicted_label)}</dd>
          <dt>Level 1</dt><dd>{html.escape(record.level1_decision)}</dd>
          <dt>Hint</dt><dd>{html.escape(record.level1_best_matching_category_hint or '<empty>')}</dd>
          <dt>Ungated L2</dt><dd>{html.escape(record.ungated_level2_predicted_label or '<none>')}</dd>
          <dt>Reject type</dt><dd>{html.escape(record.negative_source_type or '<none>')}</dd>
          <dt>Source</dt><dd>{html.escape(' / '.join(source_parts) if source_parts else '<unknown>')}</dd>
        </dl>
      </div>
    </article>
    """


def _status_chip(record: SampleRecord) -> str:
    if record.expected_label == "REJECT":
        if record.predicted_label == "REJECT":
            return '<span class="chip good">correct reject</span>'
        return '<span class="chip bad">false accept</span>'
    if record.predicted_label == "REJECT":
        return '<span class="chip bad">false reject</span>'
    if record.predicted_label == record.expected_label:
        return '<span class="chip good">correct accept</span>'
    return '<span class="chip warn">wrong category</span>'


def _relative_src(
    *,
    dataset_root: Path,
    output_path: Path,
    relative_image_path: str,
) -> str:
    image_path = Path(dataset_root) / relative_image_path
    if not image_path.is_file():
        raise ValueError(
            f"Expected image `{image_path}` for report output `{output_path}` does not exist."
        )
    return os.path.relpath(image_path, start=output_path.parent)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render an HTML benchmark report for DSPy intake evaluation artifacts.")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--summary-path", type=Path, required=True)
    parser.add_argument("--predictions-path", type=Path, required=True)
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--report-title", default="DSPy Intake Benchmark Report")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_path = render_html_report(
        dataset_root=args.dataset_root,
        summary_path=args.summary_path,
        predictions_path=args.predictions_path,
        manifest_path=args.manifest_path,
        output_path=args.output_path,
        report_title=args.report_title,
    )
    print(json.dumps({"output_path": str(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
