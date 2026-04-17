#!/usr/bin/env bash
set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${PORT:-8501}"

# If API_URL is not provided, point Streamlit to the local backend in this same container.
export API_URL="${API_URL:-http://127.0.0.1:${BACKEND_PORT}}"

echo "[railway] Starting backend on ${BACKEND_PORT}"
uvicorn app.main:app --host 127.0.0.1 --port "${BACKEND_PORT}" &
BACKEND_PID=$!

sleep 2
if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
  echo "[railway] Backend failed to start"
  wait "${BACKEND_PID}"
fi

echo "[railway] Starting frontend on ${FRONTEND_PORT}"
exec streamlit run ui/streamlit_app.py \
  --server.address 0.0.0.0 \
  --server.port "${FRONTEND_PORT}" \
  --logger.level=error \
  --client.showErrorDetails=false \
  --client.toolbarMode=minimal
