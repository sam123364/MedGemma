import { expect, test } from "@playwright/test";

test("patient run completes with timeline, safety warning, chat, and population map", async ({ page }) => {
  await page.goto("/");

  await page.getByLabel("eGFR").fill("18");
  await page.getByRole("button", { name: "Launch Astra-Gemma Run" }).click();

  await expect(page).toHaveURL(/\/run\/run-/);
  const timeline = page.locator("section", { hasText: "Agentic Workflow Timeline" });
  await expect(timeline).toBeVisible();
  await expect(timeline.getByText("run.started", { exact: true })).toBeVisible({ timeout: 30_000 });
  await expect(timeline.getByText("protocols.generated", { exact: true })).toBeVisible({ timeout: 60_000 });
  await expect(timeline.getByText("run.completed", { exact: true })).toBeVisible({ timeout: 120_000 });

  await expect(page.getByText("Ranked Protocol Board")).toBeVisible();
  await expect(page.getByText("Black Box Warning")).toBeVisible();
  await expect(page.getByText("Recommendation Stability Across Patient Variants")).toBeVisible();

  await page.getByPlaceholder("Why is protocol #1 safer than #2?").fill("Why is protocol #1 preferred over #2?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByText("Research prototype disclaimer")).toBeVisible({ timeout: 30_000 });
});
