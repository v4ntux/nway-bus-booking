#!/bin/sh
set -e

PORT="${PORT:-8000}"

python - <<'PY'
from app.core.config import get_settings

get_settings().ensure_database_configured()
print("database_url_ok")
PY

alembic upgrade head

if [ "${RUN_SEED:-true}" != "false" ]; then
  python -m app.cli seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
