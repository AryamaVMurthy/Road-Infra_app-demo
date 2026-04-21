FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY . .

RUN chown -R appuser:appgroup /app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8088

USER appuser

CMD ["python", "start_backend.py"]
