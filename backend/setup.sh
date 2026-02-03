#!/bin/bash

# Exit on error
set -e

echo "Setting up backend..."

# Create .env if not exists
if [ ! -f .env ]; then
  cat <<EOF > .env
API_V1_STR=/api/v1
PROJECT_NAME="Urban Infrastructure Issue Reporting"
BACKEND_CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=toto
POSTGRES_DB=app
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=infrastructure-evidence
SECRET_KEY=$(openssl rand -hex 32)
EOF
fi

# We assume postgres and minio are running as per the prompt instructions (Use Minio for storage and any opensource DB)
# In a real environment, we'd check or start them via docker-compose

echo "Backend setup complete. Run 'uvicorn app.main:app --reload' to start."
