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
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5185",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `"${PYTHON}" -m uvicorn api.main:app --port 8135`,
      cwd: REPO_ROOT,
      env: { ROTA_DB_PATH: E2E_DB, ROTA_DEV_COORDINATOR_ID: "DEV-COORD-E2E" },
      port: 8135,
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: "npx vite --port 5185 --host 127.0.0.1",
      cwd: __dirname,
      env: { ROTA_E2E_API_PORT: "8135", ROTA_E2E_TEST_HOOKS: "1" },
      port: 5185,
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
