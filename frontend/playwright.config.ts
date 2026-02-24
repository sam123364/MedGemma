import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 120_000,
  expect: {
    timeout: 20_000,
  },
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command:
        "bash -lc 'cd ../backend && export MEDGEMMA_RUNTIME=mock ENFORCE_ALEMBIC_HEAD=false SIM_HORIZON_DAYS=30 COARSE_TRIALS=120 HIGH_FIDELITY_COUNT=2; if [ -x ../.venv312/bin/python ]; then ../.venv312/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000; else ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000; fi'",
      port: 8000,
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --port 3000",
      port: 3000,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
