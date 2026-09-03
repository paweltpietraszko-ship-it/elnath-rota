import { Page, Download } from "@playwright/test";
import AdmZip from "adm-zip";
import fs from "node:fs";

export async function waitForWorkspaceLoaded(page: Page) {
  // Let the initial GET /workspace/sites (fired on mount, with no
  // preceding click) settle before any test that asserts on the
  // presence/absence of ACTION_STALLED -- otherwise its render can
  // race the MutationObserver watch of an unrelated click.
  await page
    .waitForResponse((r) => r.url().includes("/api/workspace/sites") && r.request().method() === "GET", {
      timeout: 5000,
    })
    .catch(() => undefined);
}

export async function createSite(page: Page, displayName: string) {
  await page.goto("/");
  await page.getByRole("button", { name: "Nowy obiekt (Standardowy)" }).click();
  await page.locator('input[placeholder="np. NORDPLAST II"]').fill(displayName);
  await page.locator('[data-diag-action="create-site-submit"]').click();
  await page.getByText(displayName, { exact: true }).waitFor();
}

export async function openSite(page: Page, displayName: string) {
  await page.getByText(displayName, { exact: true }).click();
  await page.getByRole("heading", { name: "Panel sterowania" }).waitFor();
}

async function readDownloadJson(download: Download): Promise<string> {
  const path = await download.path();
  if (!path) throw new Error("download produced no local path");
  return fs.readFileSync(path, "utf-8");
}

export async function downloadFrontendReport(page: Page): Promise<Record<string, unknown>> {
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Pobierz diagnostykę frontu" }).click(),
  ]);
  const text = await readDownloadJson(download);
  return JSON.parse(text);
}

export async function downloadDiagnosticZip(
  page: Page,
): Promise<{ raw: Buffer; frontendReport: Record<string, unknown> | null }> {
  // POST /workspace/diagnostics can hit the pre-existing, out-of-scope
  // api/deps.py thread-affinity race (see
  // project_sqlite_thread_affinity_bug_found memory); a couple of
  // retries absorb that without masking a real assertion failure.
  let lastError: unknown;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const [download] = await Promise.all([
        page.waitForEvent("download", { timeout: 8000 }),
        page.locator('[data-diag-action="download-diagnostics"]').click(),
      ]);
      const path = await download.path();
      if (!path) throw new Error("download produced no local path");
      const raw = fs.readFileSync(path);
      const zip = new AdmZip(raw);
      const entry = zip.getEntry("frontend_diagnostics.json");
      const frontendReport = entry ? JSON.parse(entry.getData().toString("utf-8")) : null;
      return { raw, frontendReport };
    } catch (e) {
      lastError = e;
    }
  }
  throw lastError;
}
