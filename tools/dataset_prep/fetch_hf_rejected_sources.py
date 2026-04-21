"""Fetch rejected-source images from Hugging Face rows APIs.

Supports both:
- real irrelevant negatives
- synthetic spoof negatives
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import httpx

from tools.dataset_prep.common import (
    DatasetBuildError,
    NegativeImageSourceRecord,
    load_dataset_config,
    resolve_output_root,
)


ROWS_API_URL = "https://datasets-server.huggingface.co/rows"
SIZE_API_URL = "https://datasets-server.huggingface.co/size"


def build_rejected_dataset_filename(index: int, source_page_title: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "_", source_page_title.lower()).strip("_")
    return f"{index:03d}_{stem[:80] or 'sample'}.jpg"


def fetch_rejected_dataset_sources(config_path: Path) -> Path:
    config = load_dataset_config(config_path)
    sources = list(config.get("rejected_dataset_sources", []))
    if not sources:
        raise DatasetBuildError(
            "Dataset config must declare `rejected_dataset_sources` before fetching rejected samples."
        )

    output_root = resolve_output_root(config_path, config)
    output_root.mkdir(parents=True, exist_ok=True)
    min_short_edge = int(config.get("min_short_edge", 256))

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for source in sources:
            _fetch_single_source(
                client=client,
                source=source,
                output_root=output_root,
                min_short_edge=min_short_edge,
            )

    return output_root


def _fetch_single_source(
    *,
    client: httpx.Client,
    source: dict[str, Any],
    output_root: Path,
    min_short_edge: int,
) -> None:
    dataset_id = str(source["dataset_id"])
    config_name = str(source.get("config_name", "default"))
    split_name = str(source.get("split", "train"))
    image_field = str(source.get("image_field", "image"))
    output_dir = output_root / str(source["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    target_count = int(source["count"])

    existing_sidecars = sorted(output_dir.glob("*.json"))
    if len(existing_sidecars) >= target_count:
        return

    total_rows = _fetch_split_row_count(
        client=client,
        dataset_id=dataset_id,
        config_name=config_name,
        split_name=split_name,
    )
    page_length = int(source.get("page_length", 50))
    filter_values = {str(value) for value in source.get("filter_values", [])}
    filter_field = source.get("filter_field")
    label_field = source.get("label_field")
    diversity_field = source.get("diversity_field")
    max_per_diversity_value = source.get("max_per_diversity_value")
    source_dataset_field = source.get("source_dataset_field")
    source_license_field = source.get("source_license_field")
    source_title_field = source.get("source_title_field")
    topic_bucket = str(source["topic_bucket"])
    negative_source_type = str(source["negative_source_type"])

    saved_count = 0
    diversity_counts: dict[str, int] = {}

    for sidecar_path in existing_sidecars:
        sidecar = NegativeImageSourceRecord.model_validate_json(sidecar_path.read_text("utf-8"))
        saved_count += 1
        diversity_value = sidecar.source_dataset
        diversity_counts[diversity_value] = diversity_counts.get(diversity_value, 0) + 1

    offset = 0
    while offset < total_rows and saved_count < target_count:
        page = _fetch_rows_page(
            client=client,
            dataset_id=dataset_id,
            config_name=config_name,
            split_name=split_name,
            offset=offset,
            length=page_length,
        )
        feature_map = {
            str(feature["name"]): feature.get("type", {})
            for feature in page.get("features", [])
            if isinstance(feature, dict) and "name" in feature
        }
        rows = list(page.get("rows", []))
        if not rows:
            break
        for row_item in rows:
            row = row_item["row"]
            if filter_field is not None:
                resolved_filter_value = _resolve_row_value(
                    raw_value=row.get(str(filter_field)),
                    feature_type=feature_map.get(str(filter_field), {}),
                )
                if str(resolved_filter_value) not in filter_values:
                    continue

            if diversity_field is not None and max_per_diversity_value is not None:
                diversity_value = str(
                    _resolve_row_value(
                        raw_value=row.get(str(diversity_field)),
                        feature_type=feature_map.get(str(diversity_field), {}),
                    )
                )
                if diversity_counts.get(diversity_value, 0) >= int(max_per_diversity_value):
                    continue
            else:
                diversity_value = dataset_id

            image_info = row.get(image_field)
            if not isinstance(image_info, dict) or "src" not in image_info:
                raise DatasetBuildError(
                    f"Rejected dataset `{dataset_id}` row is missing image src in field `{image_field}`"
                )

            width = image_info.get("width")
            height = image_info.get("height")
            if not isinstance(width, int) or not isinstance(height, int):
                raise DatasetBuildError(
                    f"Rejected dataset `{dataset_id}` row is missing integer width/height metadata"
                )
            if min(width, height) < min_short_edge:
                continue

            source_dataset = (
                str(row.get(str(source_dataset_field)))
                if source_dataset_field and row.get(str(source_dataset_field)) is not None
                else dataset_id
            )
            license_name = (
                str(row.get(str(source_license_field)))
                if source_license_field and row.get(str(source_license_field)) is not None
                else str(source["license_name"])
            )
            source_page_title = (
                str(row.get(str(source_title_field)))
                if source_title_field and row.get(str(source_title_field)) is not None
                else (
                    f"{_resolve_row_value(raw_value=row.get(str(label_field)), feature_type=feature_map.get(str(label_field), {}))} sample {saved_count + 1:04d}"
                    if label_field and row.get(str(label_field)) is not None
                    else f"{source_dataset.replace('/', ' ')} sample {saved_count + 1:04d}"
                )
            )

            saved_count += 1
            filename = build_rejected_dataset_filename(saved_count, source_page_title)
            image_path = output_dir / filename
            sidecar_path = image_path.with_suffix(image_path.suffix + ".json")
            if image_path.is_file() and sidecar_path.is_file():
                diversity_counts[diversity_value] = diversity_counts.get(diversity_value, 0) + 1
                continue

            _download_image(client=client, image_url=str(image_info["src"]), destination=image_path)
            sidecar = NegativeImageSourceRecord(
                topic_bucket=topic_bucket,
                source_dataset=source_dataset,
                source_url=(
                    f"https://huggingface.co/datasets/{source_dataset}"
                    if "/" in source_dataset
                    else str(source["source_url"])
                ),
                source_page_title=source_page_title,
                license_name=license_name,
                license_url=str(source.get("license_url", source["source_url"])),
                author_or_uploader=str(source["author_or_uploader"]),
                negative_source_type=negative_source_type,
                is_spoof=negative_source_type == "synthetic_spoof",
                notes=str(source.get("notes")) if source.get("notes") is not None else None,
            )
            sidecar_path.write_text(sidecar.model_dump_json(indent=2) + "\n", encoding="utf-8")
            diversity_counts[diversity_value] = diversity_counts.get(diversity_value, 0) + 1

            if saved_count >= target_count:
                break
        offset += page_length

    if saved_count < target_count:
        raise DatasetBuildError(
            f"Rejected dataset `{dataset_id}` yielded only {saved_count} samples; need at least {target_count}"
        )


def _resolve_row_value(*, raw_value: Any, feature_type: dict[str, Any]) -> str | int | float | None:
    names = feature_type.get("names")
    if isinstance(names, list) and isinstance(raw_value, int):
        if 0 <= raw_value < len(names):
            return str(names[raw_value])
    return raw_value


def _fetch_rows_page(
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


def _fetch_split_row_count(
    *,
    client: httpx.Client,
    dataset_id: str,
    config_name: str,
    split_name: str,
) -> int:
    response = _request_with_retry(
        client=client,
        url=SIZE_API_URL,
        params={"dataset": dataset_id},
    )
    payload = response.json()
    split_rows = payload.get("size", {}).get("splits", [])
    for split in split_rows:
        if split.get("config") == config_name and split.get("split") == split_name:
            num_rows = split.get("num_rows")
            if not isinstance(num_rows, int) or num_rows <= 0:
                raise DatasetBuildError(
                    f"Rows API size payload returned invalid num_rows for `{dataset_id}` `{split_name}`"
                )
            return num_rows
    raise DatasetBuildError(
        f"Rows API size payload did not include split `{split_name}` for `{dataset_id}` `{config_name}`"
    )


def _download_image(
    *,
    client: httpx.Client,
    image_url: str,
    destination: Path,
) -> None:
    response = _request_with_retry(client=client, url=image_url)
    destination.write_bytes(response.content)


def _request_with_retry(
    *,
    client: httpx.Client,
    url: str,
    params: dict[str, Any] | None = None,
    max_attempts: int = 10,
) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.get(url, params=params)
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt < max_attempts:
                time.sleep(float(max(attempt * 5, 10)))
                continue
            raise DatasetBuildError(str(exc)) from exc

        if response.status_code in {429, 500, 502, 503, 504} and attempt < max_attempts:
            retry_after = response.headers.get("Retry-After")
            wait_seconds = float(retry_after) if retry_after else float(max(attempt * 5, 10))
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
    fetch_rejected_dataset_sources(args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
