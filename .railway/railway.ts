// ROTA-CLOUD-REVIEW-FIXES R: Railway Infrastructure as Code for the ONE
// existing service of this repo (project truthful-freedom, service
// elnath-rota), replacing the deprecated railway.json (Config as Code works
// only until 2026-12-01).
//
// Imported from the live project with `railway config pull` (2026-10-16),
// then ONLY these were added:
//   - build: DOCKERFILE + Dockerfile -- the live service-level builder is
//     RAILPACK; until 2026-10-16 only railway.json forced the Dockerfile. Without this
//     line Railway would silently build without it (no PDF fonts, no TZ, no
//     frontend) -- the 2026-09-17 incident in deploy/RAILWAY.md.
//   - branch "main" (the live source branch) and the named single-service
//     partial.
// Everything else mirrors the live state on purpose: an OMITTED field is
// not "left alone" -- `railway config plan` showed that leaving out env,
// volumeMounts or source DELETES every secret (incl. ROTA_CENTRAL_KEK, the
// PII encryption key), detaches /data and unlinks the repo. preserve() keeps
// each secret's current value on Railway; no value is ever stored here.
//
// Nothing here is applied by a git push. Apply only through the CLI, after
// `railway config plan` shows exactly one change (build.builder) and the
// owner approved it -- deploy/RAILWAY.md, "Migracja z railway.json".
import { defineRailway, github, preserve, project, service, volume } from "railway/iac";

// This repository manages only its own resources in the environment.
// See https://docs.railway.com/infrastructure-as-code#multi-repo-projects
export const partial = "elnath-rota";

export default defineRailway(() => {
  const elnathRotaVolume = volume("elnath-rota-volume", {
    alerts: { usage: { "100": {}, "80": {}, "95": {} } },
    allowOnlineResize: true,
    region: "us-east4-eqdc4a",
    sizeMB: 5000,
  });
  const elnathRota = service("elnath-rota", {
    source: github("paweltpietraszko-ship-it/elnath-rota", { branch: "main", checkSuites: false }),
    build: { builder: "DOCKERFILE", dockerfilePath: "Dockerfile" },
    replicas: { "us-east4-eqdc4a": 1 },
    volumeMounts: { "/data": elnathRotaVolume },
    env: {
      ROTA_ACCOUNTS_DB_DIR: preserve(),
      ROTA_ALLOWED_ORIGINS: preserve(),
      ROTA_AUTH_DB_PATH: preserve(),
      ROTA_AUTH_SECRET: preserve(),
      ROTA_CENTRAL_KEK: preserve(),
      ROTA_DB_PATH: preserve(),
    },
  });

  return project("truthful-freedom", {
    resources: [elnathRota, elnathRotaVolume],
  });
});
