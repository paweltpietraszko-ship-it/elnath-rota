import { test, expect, type Page } from "@playwright/test";
import { waitForWorkspaceLoaded } from "./helpers";

type Event = {
  kind: string;
  action_id?: string | null;
  action?: string;
};

async function events(page: Page): Promise<Event[]> {
  const raw = await page.evaluate(() => sessionStorage.getItem("elnath-rota-diag-buffer"));
  return raw ? (JSON.parse(raw) as Event[]) : [];
}

test("audit R2: an unrelated mutation inside another root branch cannot hide a dead control", async ({ page }) => {
  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.locator('[data-diag-action="diag-test-inert"]').click();
  await page.evaluate(() => {
    setTimeout(() => {
      document.getElementById("root")!.setAttribute("data-unrelated-refresh", "complete");
    }, 100);
  });
  await page.waitForTimeout(1000);

  const recorded = await events(page);
  expect(recorded.some((event) => event.kind === "ACTION_STALLED" && event.action === "diag-test-inert")).toBe(true);
});

test("audit R2: a delayed error resolves its causal click rather than a newer click", async ({ page }) => {
  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.evaluate(() => {
    const root = document.getElementById("root")!;
    const delayedError = document.createElement("button");
    delayedError.dataset.diagAction = "audit-delayed-error";
    delayedError.textContent = "delayed error";
    delayedError.addEventListener("click", () => {
      setTimeout(() => {
        throw new Error("audit delayed error");
      }, 300);
    });

    const laterInert = document.createElement("button");
    laterInert.dataset.diagAction = "audit-later-inert";
    laterInert.textContent = "later inert";
    root.append(delayedError, laterInert);
  });

  await page.locator('[data-diag-action="audit-delayed-error"]').click();
  await page.waitForTimeout(50);
  await page.locator('[data-diag-action="audit-later-inert"]').click();
  await page.waitForTimeout(1000);

  const recorded = await events(page);
  const first = recorded.find((event) => event.kind === "CLICK_RECEIVED" && event.action === "audit-delayed-error");
  const second = recorded.find((event) => event.kind === "CLICK_RECEIVED" && event.action === "audit-later-inert");
  const stalled = recorded.filter((event) => event.kind === "ACTION_STALLED");

  expect.soft(stalled.some((event) => event.action_id === first?.action_id)).toBe(false);
  expect.soft(stalled.some((event) => event.action_id === second?.action_id)).toBe(true);
});
