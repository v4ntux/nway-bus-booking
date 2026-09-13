#!/bin/sh
set -e

PORT="${PORT:-8000}"

alembic upgrade head

if [ "${RUN_SEED:-true}" != "false" ]; then
  python -m app.cli seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
