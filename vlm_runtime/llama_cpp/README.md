# llama.cpp Runtime

This directory contains the first live runtime gate for the AI intake filter.

## Default model

- Repo: `LiquidAI/LFM2.5-VL-1.6B-GGUF`
- Quantization: `Q8_0`
- Endpoint: `http://localhost:8081/v1/chat/completions`

## Start with Docker Compose

```bash
docker compose up -d llama-server
```

## Smoke test

```bash
python3 vlm_runtime/llama_cpp/smoke_test.py
```

The smoke test sends a multimodal OpenAI-style request and validates that the
response can be parsed against the gateway contract.

## Environment variables

- `LLAMA_MODEL_REPO`
- `LLAMA_MODEL_QUANT`
- `LLAMA_HOST`
- `LLAMA_PORT`
- `LLAMA_CTX_SIZE`
- `LLAMA_PARALLEL`
- `LLAMA_THREADS`
