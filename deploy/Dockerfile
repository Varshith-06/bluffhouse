# Build context is the repo root: docker build -f deploy/Dockerfile .
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.8 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    BLUFFHOUSE_RUNS=/app/runs

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev --no-editable

COPY deploy/server.py ./server.py

# Bake in the scripted demo game so the hub has something to show on a cold
# container. Storage is ephemeral, so anything written at runtime is lost on
# redeploy; this run is deterministic and needs no API keys. The directory
# name matches serve.DEMO_DIR, so the app's "run demo" button finds it.
RUN python -c "\
from pathlib import Path; \
from bluffhouse.demo import demo_game; \
demo_game().write(Path('/app/runs/demo-seed11'))"

EXPOSE 8080
CMD ["python", "server.py"]
