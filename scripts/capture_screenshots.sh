#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${ROOT_DIR}/frontend"
npx playwright test tests/e2e/capture.spec.ts --project=chromium

echo "Screenshots written to ${ROOT_DIR}/output/screenshots"
