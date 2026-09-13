import { test, expect } from "@playwright/test";
import { waitForWorkspaceLoaded } from "./helpers";

type Event = {
  kind: string;
  action_id?: string | null;
  action?: string;
  endpoint_template?: string;
  error_category?: string;
};

async function events(page: import("@playwright/test").Page): Promise<Event[]> {
  const raw = await page.evaluate(() => sessionStorage.getItem("elnath-rota-diag-buffer"));
  return raw ? (JSON.parse(raw) as Event[]) : [];
}

test("audit R1: a SITE identifier is removed from recorded endpoint paths", async ({ page }) => {
  const suffix = Math.random().toString(36).slice(2, 10);
  const responsePromise = page.waitForResponse(
    (response) => response.url().endsWith("/api/workspace/sites") && response.request().method() === "POST",
  );

  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.getByRole("button", { name: "Nowy obiekt (Standardowy)" }).click();
  await page.locator('input[placeholder="np. NORDPLAST II"]').fill(`AUDIT-${suffix}`);
  await page.locator('[data-diag-action="create-site-submit"]').click();

  const created = (await (await responsePromise).json()) as { site_id: string };
  await page.getByText(`AUDIT-${suffix}`, { exact: true }).click();
  // ROTA-E2E-AUDIT-R1-TESTS-STALE (Codex R1, exact 40d1e95): "Panel
  // sterowania" is Room's nav button (visible on the default "Przegląd"
  // landing tab), not a heading that only renders once that tab is
  // actually selected -- the old wait never resolved, so this test never
  // reached its real assertion below.
  await page.getByRole("button", { name: "Panel sterowania" }).waitFor();

  const serialized = JSON.stringify(await events(page));
  expect(serialized).not.toContain(created.site_id);
});

test("audit R1: a registered unhandled error resolves its originating action", async ({ page }) => {
  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.locator('[data-diag-action="diag-test-unhandled-error"]').click();
  await page.waitForTimeout(1000);

  const recorded = await events(page);
  const click = recorded.find((event) => event.action === "diag-test-unhandled-error");
  expect(recorded.some((event) => event.kind === "UNHANDLED_ERROR")).toBe(true);
  expect(recorded.some((event) => event.kind === "ACTION_STALLED" && event.action_id === click?.action_id)).toBe(false);
});

test("audit R1: an unrelated DOM mutation cannot hide a dead control", async ({ page }) => {
  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.locator('[data-diag-action="diag-test-inert"]').click();
  await page.evaluate(() => {
    setTimeout(() => document.body.setAttribute("data-unrelated-mutation", "1"), 100);
  });
  await page.waitForTimeout(1000);

  const recorded = await events(page);
  expect(recorded.some((event) => event.kind === "ACTION_STALLED" && event.action === "diag-test-inert")).toBe(true);
});

test("audit R1: malformed successful JSON is classified as a request failure", async ({ page }) => {
  await page.route("**/api/workspace/sites", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 201, contentType: "application/json", body: "{" });
    } else {
      await route.continue();
    }
  });

  await page.goto("/");
  await waitForWorkspaceLoaded(page);
  await page.getByRole("button", { name: "Nowy obiekt (Standardowy)" }).click();
  await page.locator('input[placeholder="np. NORDPLAST II"]').fill("AUDIT-PARSE");
  await page.locator('[data-diag-action="create-site-submit"]').click();
  await page.locator(".banner-error").waitFor();

  const recorded = await events(page);
  expect(
    recorded.some(
      (event) =>
        event.kind === "REQUEST_FAILED" &&
        event.endpoint_template === "/workspace/sites" &&
        event.error_category === "parse",
    ),
  ).toBe(true);
});

// ROTA-E2E-AUDIT-R1-TESTS-STALE (Codex R1, exact 40d1e95): removed
// "audit R1: ordinary dev runtime has no clickable failure-injection
// controls" -- playwright.config.ts's single shared webServer sets
// ROTA_E2E_TEST_HOOKS=1 for the whole suite (vite.config.ts turns that
// into __E2E_TEST_HOOKS__=true), so App.tsx correctly renders TestHooks
// here; this test could never assert "ordinary dev" from inside that
// config. Codex independently reconfirmed the actual guarantee by
// running plain `vite dev` without the flag on this exact commit:
// test_hook_buttons = 0, matching T021c's own accepted audit R6.
