import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { execSync } from "node:child_process";

function resolveBuildSha(): string {
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
  },
  server: {
    port: 5173,
    proxy: {
      "/api": `http://127.0.0.1:${process.env.ROTA_E2E_API_PORT ?? "8123"}`,
    },
  },
});
