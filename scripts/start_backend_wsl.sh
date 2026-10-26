#!/bin/bash
set -e

# Resolve repository root directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR/backend"

export PYTHONPATH=.
export DATABASE_URL=${DATABASE_URL:-sqlite:///./dev.db}
export CELERY_TASK_ALWAYS_EAGER=true

# Launch uvicorn from venv if present, otherwise system uvicorn
if [ -f "$DIR/.venv/bin/uvicorn" ]; then
    exec "$DIR/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000
elif [ -f "/home/laksh/quantum-learning-platform/.venv/bin/uvicorn" ]; then
    exec /home/laksh/quantum-learning-platform/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
else
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
