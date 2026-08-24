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

test("audit R3: a causal local UI update at 100 ms resolves its click", async ({ page }) => {
  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.evaluate(() => {
    const control = document.createElement("button");
    control.dataset.diagAction = "audit-delayed-ui-effect";
    control.textContent = "delayed UI effect";
    control.addEventListener("click", () => {
      setTimeout(() => control.setAttribute("data-result", "done"), 100);
    });
    document.getElementById("root")!.append(control);
  });

  await page.locator('[data-diag-action="audit-delayed-ui-effect"]').click();
  await page.waitForFunction(() =>
    document.querySelector('[data-diag-action="audit-delayed-ui-effect"]')?.getAttribute("data-result") === "done",
  );
  await page.waitForTimeout(900);

  const recorded = await events(page);
  const click = recorded.find(
    (event) => event.kind === "CLICK_RECEIVED" && event.action === "audit-delayed-ui-effect",
  );
  expect(recorded.some((event) => event.kind === "ACTION_STALLED" && event.action_id === click?.action_id)).toBe(false);
});

test("audit R3: a delayed rejected promise resolves its causal click, not a newer click", async ({ page }) => {
  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.evaluate(() => {
    const root = document.getElementById("root")!;
    const delayedRejection = document.createElement("button");
    delayedRejection.dataset.diagAction = "audit-delayed-rejection";
    delayedRejection.textContent = "delayed rejection";
    delayedRejection.addEventListener("click", () => {
      setTimeout(() => {
        void Promise.reject(new Error("audit delayed rejection"));
      }, 300);
    });

    const laterInert = document.createElement("button");
    laterInert.dataset.diagAction = "audit-later-inert-after-rejection";
    laterInert.textContent = "later inert";
    root.append(delayedRejection, laterInert);
  });

  await page.locator('[data-diag-action="audit-delayed-rejection"]').click();
  await page.waitForTimeout(50);
  await page.locator('[data-diag-action="audit-later-inert-after-rejection"]').click();
  await page.waitForTimeout(1000);

  const recorded = await events(page);
  const first = recorded.find(
    (event) => event.kind === "CLICK_RECEIVED" && event.action === "audit-delayed-rejection",
  );
  const second = recorded.find(
    (event) => event.kind === "CLICK_RECEIVED" && event.action === "audit-later-inert-after-rejection",
  );
  const stalled = recorded.filter((event) => event.kind === "ACTION_STALLED");

  expect.soft(recorded.some((event) => event.kind === "UNHANDLED_REJECTION")).toBe(true);
  expect.soft(stalled.some((event) => event.action_id === first?.action_id)).toBe(false);
  expect.soft(stalled.some((event) => event.action_id === second?.action_id)).toBe(true);
});
