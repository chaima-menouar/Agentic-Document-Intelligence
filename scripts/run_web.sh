#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v node >/dev/null || ! command -v npm >/dev/null; then
  echo 'Node.js 22.12+ and npm are required. In Codespaces: nvm install 22 && nvm use 22'
  exit 1
fi
python -m pip install -r requirements-all.txt
npm --prefix frontend ci
npm --prefix frontend run build
exec python -m uvicorn app.web.api:app --host 0.0.0.0 --port "${PORT:-8501}" --workers 1
