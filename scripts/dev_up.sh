#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TIMEOUT_SECONDS="${STARTUP_TIMEOUT_SECONDS:-900}"
POLL_INTERVAL_SECONDS=5

require_command() {
    local command_name="$1"
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Missing required command: $command_name" >&2
        exit 1
    fi
}

service_container_id() {
    docker compose ps -q "$1"
}

service_state() {
    local service_name="$1"
    local container_id

    container_id="$(service_container_id "$service_name")"
    if [[ -z "$container_id" ]]; then
        echo "missing"
        return 0
    fi

    docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id"
}

configure_docker_client() {
    if docker info >/dev/null 2>&1; then
        return 0
    fi

    if [[ -S /var/run/docker.sock && "${DOCKER_HOST:-}" != "unix:///var/run/docker.sock" ]]; then
        export DOCKER_HOST="unix:///var/run/docker.sock"
        if docker info >/dev/null 2>&1; then
            echo "Using Docker daemon at $DOCKER_HOST"
            return 0
        fi
    fi

    echo "Unable to talk to Docker Compose." >&2
    echo "Check that Docker is running and that your current user can reach the daemon." >&2
    exit 1
}

wait_for_service() {
    local service_name="$1"
    local expected_state="$2"
    local start_epoch
    local current_state

    start_epoch="$(date +%s)"

    while true; do
        current_state="$(service_state "$service_name")"
        if [[ "$current_state" == "$expected_state" ]]; then
            printf 'Service %-12s %s\n' "$service_name" "$current_state"
            return 0
        fi

        if (( "$(date +%s)" - start_epoch >= TIMEOUT_SECONDS )); then
            echo "Timed out waiting for service '$service_name' to reach '$expected_state'. Current state: '$current_state'." >&2
            echo "Inspect with: docker compose logs $service_name" >&2
            exit 1
        fi

        sleep "$POLL_INTERVAL_SECONDS"
    done
}

require_command docker
configure_docker_client

echo "Bringing up the full local AI intake stack..."
docker compose up -d --build db minio redis llama-server vlm-gateway backend frontend

echo "Waiting for healthy dependencies and running app services..."
wait_for_service db healthy
wait_for_service minio healthy
wait_for_service redis healthy
wait_for_service llama-server healthy
wait_for_service vlm-gateway running
wait_for_service backend running
wait_for_service frontend running

cat <<'EOF'

Local stack is up.

Open:
- Frontend: http://localhost:3011
- API docs (via frontend proxy): http://localhost:3011/api/v1/docs
- VLM gateway docs: http://localhost:8090/docs
- llama-server health: http://localhost:8081/health
- MinIO console: http://localhost:9011

Seeded users:
- citizen@example.com
- admin@authority.gov.in
- worker@authority.gov.in
- sysadmin@marg.gov.in

Notes:
- First llama.cpp start can take time because the GGUF model may need to download into the Docker volume cache.
- Citizen issue reports are AI-screened for spam/relevance only.
- Accepted reports enter the workflow uncategorized until an admin assigns the category manually.
EOF
