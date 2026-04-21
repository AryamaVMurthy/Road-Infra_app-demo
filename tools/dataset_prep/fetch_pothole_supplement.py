"""Fetch supplemental pothole images from Hugging Face rows APIs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import httpx

from tools.dataset_prep.common import DatasetBuildError, load_dataset_config, resolve_output_root


ROWS_API_URL = "https://datasets-server.huggingface.co/rows"
SIZE_API_URL = "https://datasets-server.huggingface.co/size"


def fetch_supplement_sources(
    *,
    config_path: Path,
    required_counts: dict[str, int] | None = None,
) -> Path:
    config = load_dataset_config(config_path)
    output_root = resolve_output_root(config_path, config)
    output_root.mkdir(parents=True, exist_ok=True)

    target_counts = required_counts or {
        key: value
        for key, value in dict(config["target_counts"]).items()
        if key not in {"rejected_real_irrelevant", "rejected_synthetic_spoof"}
    }
    min_short_edge = int(config.get("min_short_edge", 256))

    supplement_sources = [
        source for source in config["positive_sources"]
        if source.get("mirror_label_field") == "none"
    ]

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for index, source in enumerate(supplement_sources):
            canonical_label = list(source["label_mapping"].values())[0]
            target_total = int(target_counts.get(canonical_label, 0))
            if target_total <= 0:
                continue

            current_total = _count_existing_canonical_samples(
                canonical_label=canonical_label,
                config=config,
                output_root=output_root,
            )
            remaining_target = max(target_total - current_total, 0)
            remaining_sources = len(supplement_sources) - index
            if remaining_target <= 0:
                continue
            quota = (remaining_target + remaining_sources - 1) // remaining_sources

            _fetch_single_label(
                client=client,
                source=source,
                output_root=output_root,
                needed=quota,
                min_short_edge=min_short_edge,
            )

    return output_root


def _fetch_single_label(
    *,
    client: httpx.Client,
    source: dict[str, Any],
    output_root: Path,
    needed: int,
    min_short_edge: int,
) -> None:
    output_dir = output_root / str(source["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    existing = len(list(output_dir.glob("*.jpg")))
    fetch_margin = int(source.get("mirror_fetch_margin", 10))
    target = existing + needed + fetch_margin
    if existing >= target:
        return

    dataset_id = str(source["mirror_dataset_id"])
    config_name = str(source.get("mirror_config_name", "full"))
    split_name = str(source.get("mirror_split", "train"))
    image_field = str(source.get("mirror_image_field", "image"))
    total_rows = _fetch_split_row_count(
        client=client,
        dataset_id=dataset_id,
        config_name=config_name,
        split_name=split_name,
    )

    page_length = int(source.get("page_length", 50))
    saved = existing
    offset = 0
    while offset < total_rows and saved < target:
        page = _fetch_rows_page(
            client=client,
            dataset_id=dataset_id,
            config_name=config_name,
            split_name=split_name,
            offset=offset,
            length=page_length,
        )
        rows = list(page.get("rows", []))
        if not rows:
            break
        for row_item in rows:
            row = row_item["row"]
            image_info = row.get(image_field)
            if not isinstance(image_info, dict) or "src" not in image_info:
                raise DatasetBuildError(
                    f"Supplement dataset `{dataset_id}` row is missing image src in field `{image_field}`"
                )
            width = image_info.get("width")
            height = image_info.get("height")
            if not isinstance(width, int) or not isinstance(height, int):
                raise DatasetBuildError(
                    f"Supplement dataset `{dataset_id}` row is missing integer width/height metadata"
                )
            if min(width, height) < min_short_edge:
                continue

            saved += 1
            image_path = output_dir / f"{saved:04d}.jpg"
            if not image_path.exists():
                _download_binary(client=client, url=str(image_info["src"]), destination=image_path)
            if saved >= target:
                break
        offset += page_length

    if saved < target:
        raise DatasetBuildError(
            f"Supplement dataset `{dataset_id}` yielded only {saved} images; need at least {target}"
        )


def _count_existing_canonical_samples(
    *,
    canonical_label: str,
    config: dict[str, Any],
    output_root: Path,
) -> int:
    total = 0
    for source in config["positive_sources"]:
        output_dir = output_root / str(source["output_dir"])
        if not output_dir.exists():
            continue
        label_mapping = dict(source["label_mapping"])
        if source.get("mirror_label_field") == "none":
            if canonical_label in label_mapping.values():
                total += len(list(output_dir.glob("*.jpg")))
            continue
        for source_label, mapped_label in label_mapping.items():
            if mapped_label != canonical_label:
                continue
            total += len(list((output_dir / source_label).glob("*.jpg")))
    return total


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
    fetch_supplement_sources(config_path=args.config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
