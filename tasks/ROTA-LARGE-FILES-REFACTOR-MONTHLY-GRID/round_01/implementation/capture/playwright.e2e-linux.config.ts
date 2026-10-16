// Evidence-only config (round_01, not product): runs the repo's own
// frontend/e2e specs on this Linux container. Mirrors
// frontend/playwright.config.ts's webServer block verbatim (same commands,
// ports, e2e DB, env, global setup) -- it cannot import that file directly
// because it is ESM (import.meta) and this directory resolves as CommonJS.
// Only testDir/testMatch (E2E_MATCH regex) and the browser path differ;
// retries=2 is kept from the repo config.
// Run from frontend/:  NODE_PATH=$PWD/node_modules npx playwright test \
//   --config ../tasks/ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID/round_01/implementation/capture/playwright.e2e-linux.config.ts
import path from "node:path";

const FRONTEND = path.resolve(__dirname, "../../../../../frontend");
const REPO_ROOT = path.resolve(FRONTEND, "..");
const PYTHON = path.join(REPO_ROOT, ".venv", "Scripts", "python.exe");
const E2E_DB = path.join(REPO_ROOT, "rota_e2e.db");

export default {
  testDir: path.join(FRONTEND, "e2e"),
  testMatch: new RegExp(process.env.E2E_MATCH ?? "refactor-schedule-grid\\.spec\\.ts$"),
  globalSetup: path.join(FRONTEND, "e2e", "global-setup.ts"),
  fullyParallel: false,
  workers: 1,
  retries: 2,
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:5183", trace: "retain-on-failure" },
  webServer: [
    {
      command: `"${PYTHON}" -m uvicorn api.main:app --port 8133`,
      cwd: REPO_ROOT,
      env: { ROTA_DB_PATH: E2E_DB, ROTA_DEV_COORDINATOR_ID: "DEV-COORD-E2E" },
      port: 8133,
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: "npx vite --port 5183 --host 127.0.0.1",
      cwd: FRONTEND,
      env: { ROTA_E2E_API_PORT: "8133", ROTA_E2E_TEST_HOOKS: "1" },
      port: 5183,
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
  // The container ships Chromium 1194 at /opt/pw-browsers; Playwright 1.62
  // expects a newer build, so launch the preinstalled one explicitly.
  projects: [{ name: "chromium", use: { browserName: "chromium", launchOptions: { executablePath: "/opt/pw-browsers/chromium" } } }],
};
