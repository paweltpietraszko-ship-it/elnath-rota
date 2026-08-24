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

for (const errorKind of ["window-error", "unhandled-rejection"] as const) {
  test(`audit R5: a pre-scheduled ${errorKind} cannot resolve a later unrelated click`, async ({ page }) => {
    await page.goto("/");
    await waitForWorkspaceLoaded(page);

    await page.evaluate((kind) => {
      const inert = document.createElement("button");
      inert.dataset.diagAction = `audit-r5-inert-${kind}`;
      inert.textContent = "later unrelated inert control";
      document.getElementById("root")!.append(inert);

      // The background failure is already scheduled before the unrelated
      // click. It therefore cannot have been caused by that click, even
      // though both are delivered in adjacent browser tasks.
      setTimeout(() => {
        if (kind === "window-error") {
          throw new Error("audit R5 pre-scheduled window error");
        }
        void Promise.reject(new Error("audit R5 pre-scheduled rejection"));
      }, 0);
      inert.click();
    }, errorKind);

    await page.waitForTimeout(1000);
    const recorded = await events(page);
    const action = `audit-r5-inert-${errorKind}`;
    const click = recorded.find((event) => event.kind === "CLICK_RECEIVED" && event.action === action);
    const failureKind = errorKind === "window-error" ? "UNHANDLED_ERROR" : "UNHANDLED_REJECTION";
    const failure = recorded.find((event) => event.kind === failureKind);
    const stalled = recorded.find(
      (event) => event.kind === "ACTION_STALLED" && event.action_id === click?.action_id,
    );

    expect(click?.action_id).toBeTruthy();
    expect(failure).toBeTruthy();
    expect.soft(failure?.action_id ?? null).toBeNull();
    expect.soft(stalled).toBeTruthy();
  });
}
