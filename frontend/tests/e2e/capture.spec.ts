import fs from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

const outDir = path.resolve(__dirname, "../../../output/screenshots");

test("capture deterministic demo screenshots", async ({ page }) => {
  fs.mkdirSync(outDir, { recursive: true });

  await page.goto("/");
  await expect(page.getByText("Autonomous In-Silico Trial Engine")).toBeVisible();
  await page.screenshot({ path: path.join(outDir, "01-home.png"), fullPage: true });

  await page.getByLabel("eGFR").fill("18");
  await page.getByRole("button", { name: "Launch Astra-Gemma Run" }).click();
  await expect(page).toHaveURL(/\/run\/run-/);
  await expect(page.getByText("run.completed")).toBeVisible({ timeout: 120_000 });

  await page.screenshot({ path: path.join(outDir, "02-run-complete.png"), fullPage: true });

  await expect(page.getByText("Black Box Warning")).toBeVisible();
  await page.getByText("Black Box Warning").scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(outDir, "03-black-box-warning.png"), fullPage: true });

  await expect(page.getByText("Recommendation Stability Across Patient Variants")).toBeVisible();
  await page.getByText("Recommendation Stability Across Patient Variants").scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(outDir, "04-population-map.png"), fullPage: true });
});

