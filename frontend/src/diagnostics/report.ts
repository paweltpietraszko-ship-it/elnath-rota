// T021c section 3.3/3.4: local-only frontend diagnostic export. Works
// even when the API is unreachable -- pure client-side blob download,
// no network call.

import { buildReport } from "./buffer";
import type { FrontendDiagnosticReport } from "./types";

export function getFrontendReport(): FrontendDiagnosticReport {
  return buildReport();
}

export function downloadFrontendReport() {
  const report = buildReport();
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `rota-frontend-diagnostics-${report.session_id.slice(0, 8)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
