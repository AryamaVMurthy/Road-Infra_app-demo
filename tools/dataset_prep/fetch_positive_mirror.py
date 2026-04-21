"""Fetch positive issue images from Hugging Face rows APIs into raw label folders."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys
import time
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import httpx

from tools.dataset_prep.common import DatasetBuildError, load_dataset_config, resolve_output_root

ROWS_API_URL = "https://datasets-server.huggingface.co/rows"


def fetch_positive_mirror_sources(
    *,
    config_path: Path,
    required_counts: dict[str, int] | None = None,
) -> Path:
    config = load_dataset_config(config_path)
    output_root = resolve_output_root(config_path, config)
    output_root.mkdir(parents=True, exist_ok=True)

    if required_counts is not None:
        target_counts = dict(required_counts)
    else:
        target_counts = {
            key: value
            for key, value in dict(config["target_counts"]).items()
            if key not in {"rejected_real_irrelevant", "rejected_synthetic_spoof"}
        }

    for source in config["positive_sources"]:
        if "mirror_dataset_id" not in source:
            continue
        if source.get("mirror_label_field") == "none":
            continue
        _fetch_single_positive_source(
            source=source,
            output_root=output_root,
            target_counts=target_counts,
            min_short_edge=int(config.get("min_short_edge", 384)),
        )
    return output_root


def _fetch_single_positive_source(
    *,
    source: dict[str, Any],
    output_root: Path,
    target_counts: dict[str, int],
    min_short_edge: int,
) -> None:
    label_mapping = dict(source["label_mapping"])
    relevant_source_labels = {label for label, canonical in label_mapping.items() if canonical in target_counts}
    if not relevant_source_labels:
        raise DatasetBuildError(
            f"Positive source `{source['dataset_id']}` has no labels matching the configured target counts"
        )

    fetch_margin = int(source.get("mirror_fetch_margin", 8))
    required_by_source_label = {
        source_label: target_counts[canonical_label] + fetch_margin
        for source_label, canonical_label in label_mapping.items()
        if canonical_label in target_counts
    }

    output_dir = output_root / str(source["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    existing_counts = Counter()
    for source_label in relevant_source_labels:
        label_dir = output_dir / source_label
        if label_dir.is_dir():
            existing_counts[source_label] = _count_usable_existing_images(
                label_dir=label_dir,
                min_short_edge=min_short_edge,
            )

    if all(existing_counts[source_label] >= required_by_source_label[source_label] for source_label in relevant_source_labels):
        return

    _fetch_via_rows_api(
        source=source,
        output_dir=output_dir,
        relevant_source_labels=relevant_source_labels,
        required_by_source_label=required_by_source_label,
        existing_counts=existing_counts,
        min_short_edge=min_short_edge,
    )

    missing = {
        label: required_by_source_label[label] - existing_counts[label]
        for label in relevant_source_labels
        if existing_counts[label] < required_by_source_label[label]
    }
    if missing:
        raise DatasetBuildError(
            f"Mirror dataset `{source['mirror_dataset_id']}` did not provide enough images: {missing}"
        )


def _fetch_via_rows_api(
    *,
    source: dict[str, Any],
    output_dir: Path,
    relevant_source_labels: set[str],
    required_by_source_label: dict[str, int],
    existing_counts: Counter,
    min_short_edge: int,
) -> None:
    label_field = str(source.get("mirror_label_field", "label"))
    image_field = str(source.get("mirror_image_field", "image"))
    offset_hints = dict(source.get("mirror_offset_hints", {}))
    missing_hints = [label for label in relevant_source_labels if label not in offset_hints]
    if missing_hints:
        raise DatasetBuildError(
            f"Rows API sampling requires mirror_offset_hints for every label, missing {missing_hints}"
        )

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for source_label in sorted(relevant_source_labels):
            remaining = required_by_source_label[source_label] - existing_counts[source_label]
            if remaining <= 0:
                continue
            page = _request_rows_page(
                client=client,
                dataset_id=str(source["mirror_dataset_id"]),
                config_name=str(source.get("mirror_config_name", "default")),
                split_name=str(source.get("mirror_split", "train")),
                offset=int(offset_hints[source_label]),
                length=remaining,
            )
            label_feature = next(
                (
                    feature
                    for feature in page.get("features", [])
                    if feature.get("name") == label_field
                ),
                None,
            )
            if label_feature is None:
                raise DatasetBuildError(
                    f"Rows API response for `{source['mirror_dataset_id']}` is missing label field `{label_field}`"
                )
            label_names = list(label_feature["type"]["names"])
            for row_item in page["rows"]:
                row = row_item["row"]
                row_label = str(label_names[row[label_field]])
                if row_label != source_label:
                    raise DatasetBuildError(
                        f"Rows API offset hint for `{source_label}` returned `{row_label}` instead"
                    )
                image_info = row[image_field]
                if not isinstance(image_info, dict) or "src" not in image_info:
                    raise DatasetBuildError(
                        f"Rows API image payload for `{source_label}` is missing `src`"
                    )
                width = image_info.get("width")
                height = image_info.get("height")
                if not isinstance(width, int) or not isinstance(height, int):
                    raise DatasetBuildError(
                        f"Rows API image payload for `{source_label}` is missing integer dimensions"
                    )
                if min(width, height) < min_short_edge:
                    continue
                label_dir = output_dir / source_label
                label_dir.mkdir(parents=True, exist_ok=True)
                sample_index = existing_counts[source_label] + 1
                image_path = label_dir / f"{sample_index:04d}.jpg"
                if not image_path.exists():
                    _download_binary(client=client, url=str(image_info["src"]), destination=image_path)
                existing_counts[source_label] += 1


def _request_rows_page(
    *,
    client: httpx.Client,
    dataset_id: str,
    config_name: str,
    split_name: str,
    offset: int,
    length: int,
) -> dict[str, Any]:
    response = _request_with_retry(
        client=client,
        url=ROWS_API_URL,
        params={
            "dataset": dataset_id,
            "config": config_name,
            "split": split_name,
            "offset": offset,
            "length": length,
        },
    )
    payload = response.json()
    if not isinstance(payload, dict):
        raise DatasetBuildError(f"Rows API returned a non-object payload for `{dataset_id}`")
    return payload


def _count_usable_existing_images(*, label_dir: Path, min_short_edge: int) -> int:
    from PIL import Image

    count = 0
    for image_path in label_dir.glob("*.jpg"):
        with Image.open(image_path) as image:
            width, height = image.size
        if min(width, height) >= min_short_edge:
            count += 1
    return count


def _download_binary(*, client: httpx.Client, url: str, destination: Path) -> None:
    response = _request_with_retry(client=client, url=url)
    destination.write_bytes(response.content)


def _request_with_retry(
    *,
    client: httpx.Client,
    url: str,
    params: dict[str, Any] | None = None,
    max_attempts: int = 6,
) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.get(url, params=params)
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt < max_attempts:
                time.sleep(float(attempt * 2))
                continue
            raise DatasetBuildError(str(exc)) from exc

        if response.status_code in {429, 500, 502, 503, 504} and attempt < max_attempts:
            retry_after = response.headers.get("Retry-After")
            wait_seconds = float(retry_after) if retry_after else float(attempt * 2)
            time.sleep(wait_seconds)
            continue

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise DatasetBuildError(str(exc)) from exc
        return response

    raise DatasetBuildError(str(last_error) if last_error is not None else f"GET {url} failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    fetch_positive_mirror_sources(config_path=args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
