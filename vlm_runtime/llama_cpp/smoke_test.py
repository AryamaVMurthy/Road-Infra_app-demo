#!/usr/bin/env python3
"""Smoke test for a local llama-server multimodal endpoint."""

from __future__ import annotations

import argparse
import base64
import dataclasses
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vlm_gateway.app.parser import parse_llama_chat_response
from vlm_gateway.app.prompts import (
    build_primary_classification_request,
    load_dspy_level1_prompt_source,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default="http://localhost:8081/v1/chat/completions",
        help="llama-server chat completions endpoint",
    )
    parser.add_argument(
        "--image",
        default=str(PROJECT_ROOT / "test_e2e.jpg"),
        help="local image path for the smoke test",
    )
    parser.add_argument(
        "--program-path",
        default=str(
            PROJECT_ROOT / "artifacts" / "models" / "intake_dspy" / "level1" / "gepa" / "program"
        ),
        help="compiled DSPy level 1 program directory used as the prompt source",
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    image_bytes = image_path.read_bytes()
    image_data_url = (
        "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
    )
    prompt_source = load_dspy_level1_prompt_source(Path(args.program_path))

    payload = build_primary_classification_request(
        image_data_url=image_data_url,
        reporter_notes="Smoke-test classification for a likely road issue image.",
        active_categories={
            "pothole": "Broken or missing road surface forming a visible hole or cavity.",
            "damaged_road": "Cracked, eroded, or broken road surface without a discrete pothole cavity.",
            "damaged_road_sign": "Missing, broken, bent, or unreadable roadside sign infrastructure.",
            "garbage_litter": "Visible dumped waste or litter accumulation in public roadside space.",
        },
        prompt_source=prompt_source,
    )
    payload["model"] = "LiquidAI/LFM2.5-VL-1.6B-GGUF"
    payload["max_tokens"] = 160

    request = urllib.request.Request(
        args.url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw_body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        print(f"Smoke test failed to reach llama-server: {exc}", file=sys.stderr)
        return 1

    parsed = parse_llama_chat_response(
        payload=json.loads(raw_body),
        allowed_categories={
            "pothole",
            "damaged_road",
            "damaged_road_sign",
            "garbage_litter",
        },
        prompt_version="smoke-v1",
    )
    print(json.dumps(dataclasses.asdict(parsed), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
