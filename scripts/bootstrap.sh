#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN="python3.12"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="python3.11"
else
  echo "Python 3.11+ is required. Install python3.12 or python3.11 and re-run."
  exit 1
fi

"${PYTHON_BIN}" -m venv "${ROOT_DIR}/.venv"
source "${ROOT_DIR}/.venv/bin/activate"

pip install --upgrade pip
pip install -e "${ROOT_DIR}/backend[dev]"

cd "${ROOT_DIR}/frontend"
npm install

cat <<MSG

Bootstrap complete.

1) Backend env:
   cp ${ROOT_DIR}/backend/.env.example ${ROOT_DIR}/backend/.env

2) Start dev servers:
   ${ROOT_DIR}/scripts/dev.sh

MSG
