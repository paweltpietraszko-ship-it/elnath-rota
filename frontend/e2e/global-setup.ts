import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const PYTHON = path.join(REPO_ROOT, ".venv", "Scripts", "python.exe");
const E2E_DB = path.join(REPO_ROOT, "rota_e2e.db");

export default function globalSetup() {
  execFileSync(PYTHON, [path.join(__dirname, "seed-e2e-db.py"), E2E_DB, "DEV-COORD-E2E"], {
    cwd: REPO_ROOT,
    stdio: "inherit",
  });
}
