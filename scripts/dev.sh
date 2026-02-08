#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

if [[ -d "${ROOT_DIR}/.venv" ]]; then
  VENV_DIR="${ROOT_DIR}/.venv"
elif [[ -d "${ROOT_DIR}/.venv312" ]]; then
  VENV_DIR="${ROOT_DIR}/.venv312"
else
  echo "[dev] Missing virtual environment. Run scripts/bootstrap.sh first."
  exit 1
fi

source "${VENV_DIR}/bin/activate"

(
  cd "${ROOT_DIR}/backend"
  uvicorn app.main:app --reload --port "${BACKEND_PORT}"
) &
BACK_PID=$!

(
  cd "${ROOT_DIR}/frontend"
  npm run dev -- --port "${FRONTEND_PORT}"
) &
FRONT_PID=$!

cleanup() {
  kill "${BACK_PID}" "${FRONT_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait
