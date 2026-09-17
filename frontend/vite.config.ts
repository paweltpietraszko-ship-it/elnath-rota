import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { execSync } from "node:child_process";

function resolveBuildSha(): string {
  // ROTA-RAILWAY-DEPLOY (Codex R1-01 finding on 6b84a34): the Docker build
  // context has no .git (see .dockerignore), so `git rev-parse` always
  // fails there and every production build silently got "unknown" --
  // T021c only allows that for a genuinely non-git dev build. Railway
  // exposes RAILWAY_GIT_COMMIT_SHA as a build ARG for Dockerfile deploys
  // (wired through by the Dockerfile below); prefer it when set.
  const injected = process.env.ROTA_BUILD_SHA;
  if (injected) return injected.slice(0, 7);
  try {
    return execSync("git rev-parse --short HEAD").toString().trim();
  } catch {
    // brief.md (ROTA-T021c) section 3.1: explicit "unknown" is allowed
    // in dev when the build isn't running from a git checkout.
    return "unknown";
  }
}

export default defineConfig({
  plugins: [react()],
  define: {
    __BUILD_SHA__: JSON.stringify(resolveBuildSha()),
    // R1-4 (round-1 audit): gates the diagnostic failure-injection test
    // hooks (frontend/src/diagnostics/TestHooks.tsx). Deliberately NOT
    // import.meta.env.DEV -- ordinary `npm run dev` must not expose
    // clickable self-failure controls. Only Playwright's own webServer
    // (playwright.config.ts) sets ROTA_E2E_TEST_HOOKS.
    __E2E_TEST_HOOKS__: JSON.stringify(Boolean(process.env.ROTA_E2E_TEST_HOOKS)),
    // ROTA-T024-TESTER-LOGIN-ISOLATION (brief.md section 10/11): the login
    // screen only exists for a CENTRAL_SERVICE build -- LOCAL_WINDOWS has
    // no auth surface on the backend at all (api/main.py mounts it
    // conditionally), so the frontend must not even attempt it there.
    // Set at build time for a CENTRAL_SERVICE deployment; never a runtime
    // toggle a viewer could flip.
    __CENTRAL_SERVICE__: JSON.stringify(Boolean(process.env.ROTA_CENTRAL_SERVICE)),
  },
  server: {
    port: 5173,
    proxy: {
      "/api": `http://127.0.0.1:${process.env.ROTA_E2E_API_PORT ?? "8123"}`,
    },
  },
});
