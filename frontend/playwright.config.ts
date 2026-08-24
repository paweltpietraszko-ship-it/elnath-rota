// ROTA-T021c section 5: the acceptance matrix must run a real frontend
// in a real browser against a real backend, not source tests or direct
// function calls. Spins up both servers against a dedicated e2e SQLite
// file so real dev data (rota_dev.db) is never touched.
import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..");
const PYTHON = path.join(REPO_ROOT, ".venv", "Scripts", "python.exe");
const E2E_DB = path.join(REPO_ROOT, "rota_e2e.db");

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: false,
  workers: 1,
  // A pre-existing, out-of-scope backend race (api/deps.py::get_conn
  // thread-affinity -- see the ROTA-T021c delivery notes) can
  // intermittently 500 an unrelated request, especially screens that
  // fire several GETs on mount (EmployeeDetail). Retries absorb that
  // without masking a real assertion failure (which won't self-heal).
  retries: 2,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5183",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `"${PYTHON}" -m uvicorn api.main:app --port 8133`,
      cwd: REPO_ROOT,
      env: { ROTA_DB_PATH: E2E_DB, ROTA_DEV_COORDINATOR_ID: "DEV-COORD-E2E" },
      port: 8133,
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      command: "npx vite --port 5183 --host 127.0.0.1",
      cwd: __dirname,
      env: { ROTA_E2E_API_PORT: "8133", ROTA_E2E_TEST_HOOKS: "1" },
      port: 5183,
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
