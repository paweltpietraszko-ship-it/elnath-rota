import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const PYTHON = path.join(REPO_ROOT, ".venv", "Scripts", "python.exe");
const E2E_DB = path.join(REPO_ROOT, "rota_e2e.db");

export default function globalSetup() {
  // ROTA-T063 (brief.md section 8): a reference run needs a genuinely
  // fresh dedicated database, not one that quietly accumulated state
  // (old sites, schedules) across separate CI invocations -- this file
  // previously only seeded the one coordinator row if missing and
  // otherwise left whatever was already on disk untouched (Codex's own
  // T064 round-3 note: "global setup nie czyści trwałej bazy E2E").
  // Scoped to CI=1 (the mode T63-11 requires) so local, non-CI dev runs
  // that rely on reuseExistingServer keep their existing backend/db.
  if (process.env.CI) {
    fs.rmSync(E2E_DB, { force: true });
  }
  execFileSync(PYTHON, [path.join(__dirname, "seed-e2e-db.py"), E2E_DB, "DEV-COORD-E2E"], {
    cwd: REPO_ROOT,
    stdio: "inherit",
  });
}
