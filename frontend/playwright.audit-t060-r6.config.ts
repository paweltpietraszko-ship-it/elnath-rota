import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const configDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  testDir: "./e2e",
  testMatch: "t060-audit-r6.spec.ts",
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:5186" },
  webServer: {
    command: "npx vite --port 5186 --host 127.0.0.1",
    cwd: configDir,
    port: 5186,
    reuseExistingServer: false,
    timeout: 30000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
