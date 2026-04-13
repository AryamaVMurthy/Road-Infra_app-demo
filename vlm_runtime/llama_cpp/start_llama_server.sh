#!/bin/sh
set -eu

: "${LLAMA_MODEL_REPO:=LiquidAI/LFM2.5-VL-1.6B-GGUF}"
: "${LLAMA_MODEL_QUANT:=Q8_0}"
: "${LLAMA_MODEL_FILE:=}"
: "${LLAMA_HOST:=0.0.0.0}"
: "${LLAMA_PORT:=8081}"
: "${LLAMA_CTX_SIZE:=32768}"
: "${LLAMA_PARALLEL:=1}"
: "${LLAMA_THREADS:=4}"

export LD_LIBRARY_PATH="/app:${LD_LIBRARY_PATH:-}"

echo "Starting llama-server with model repo: ${LLAMA_MODEL_REPO}"
echo "Model quant: ${LLAMA_MODEL_QUANT}"
if [ -n "${LLAMA_MODEL_FILE}" ]; then
  echo "Model file override: ${LLAMA_MODEL_FILE}"
fi
echo "Host: ${LLAMA_HOST} Port: ${LLAMA_PORT} Context: ${LLAMA_CTX_SIZE} Parallel: ${LLAMA_PARALLEL}"

set -- /app/llama-server \
  -hf "${LLAMA_MODEL_REPO}:${LLAMA_MODEL_QUANT}" \
  --host "${LLAMA_HOST}" \
  --port "${LLAMA_PORT}" \
  -c "${LLAMA_CTX_SIZE}" \
  -np "${LLAMA_PARALLEL}" \
  -t "${LLAMA_THREADS}"

if [ -n "${LLAMA_MODEL_FILE}" ]; then
  set -- "$@" --hf-file "${LLAMA_MODEL_FILE}"
fi

exec "$@"
