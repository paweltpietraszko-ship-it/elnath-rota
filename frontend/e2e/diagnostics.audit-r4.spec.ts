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

test("audit R4: a direct render error exports the originating action_id", async ({ page }) => {
  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.locator('[data-diag-action="diag-test-render-crash"]').click();
  await page.getByText("Coś poszło nie tak").waitFor();

  const recorded = await events(page);
  const click = recorded.find(
    (event) => event.kind === "CLICK_RECEIVED" && event.action === "diag-test-render-crash",
  );
  const renderError = recorded.find((event) => event.kind === "RENDER_ERROR");
  expect(click?.action_id).toBeTruthy();
  expect(renderError?.action_id).toBe(click?.action_id);
});

test("audit R4: a direct window error exports the originating action_id", async ({ page }) => {
  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.evaluate(() => {
    const control = document.createElement("button");
    control.dataset.diagAction = "audit-direct-window-error";
    control.textContent = "direct window error";
    control.addEventListener("click", () => {
      throw new Error("audit direct window error");
    });
    document.getElementById("root")!.append(control);
  });

  await page.locator('[data-diag-action="audit-direct-window-error"]').click();
  await page.waitForTimeout(100);

  const recorded = await events(page);
  const click = recorded.find(
    (event) => event.kind === "CLICK_RECEIVED" && event.action === "audit-direct-window-error",
  );
  const windowError = recorded.find((event) => event.kind === "UNHANDLED_ERROR");
  expect(click?.action_id).toBeTruthy();
  expect(windowError?.action_id).toBe(click?.action_id);
});

test("audit R4: a direct unhandled rejection exports the originating action_id", async ({ page }) => {
  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.locator('[data-diag-action="diag-test-unhandled-rejection"]').click();
  await page.waitForTimeout(100);

  const recorded = await events(page);
  const click = recorded.find(
    (event) => event.kind === "CLICK_RECEIVED" && event.action === "diag-test-unhandled-rejection",
  );
  const rejection = recorded.find((event) => event.kind === "UNHANDLED_REJECTION");
  expect(click?.action_id).toBeTruthy();
  expect(rejection?.action_id).toBe(click?.action_id);
});

test("audit R4: an ambiguous delayed rejection stays uncorrelated and resolves no click", async ({ page }) => {
  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.evaluate(() => {
    const root = document.getElementById("root")!;
    const delayedRejection = document.createElement("button");
    delayedRejection.dataset.diagAction = "audit-r4-delayed-rejection";
    delayedRejection.textContent = "delayed rejection";
    delayedRejection.addEventListener("click", () => {
      setTimeout(() => {
        void Promise.reject(new Error("audit R4 delayed rejection"));
      }, 300);
    });

    const laterInert = document.createElement("button");
    laterInert.dataset.diagAction = "audit-r4-later-inert";
    laterInert.textContent = "later inert";
    root.append(delayedRejection, laterInert);
  });

  await page.locator('[data-diag-action="audit-r4-delayed-rejection"]').click();
  await page.waitForTimeout(50);
  await page.locator('[data-diag-action="audit-r4-later-inert"]').click();
  await page.waitForTimeout(1000);

  const recorded = await events(page);
  const first = recorded.find(
    (event) => event.kind === "CLICK_RECEIVED" && event.action === "audit-r4-delayed-rejection",
  );
  const second = recorded.find(
    (event) => event.kind === "CLICK_RECEIVED" && event.action === "audit-r4-later-inert",
  );
  const rejection = recorded.find((event) => event.kind === "UNHANDLED_REJECTION");
  const stalled = recorded.filter((event) => event.kind === "ACTION_STALLED");

  expect(rejection?.action_id ?? null).toBeNull();
  expect(stalled.some((event) => event.action_id === first?.action_id)).toBe(true);
  expect(stalled.some((event) => event.action_id === second?.action_id)).toBe(true);
});
