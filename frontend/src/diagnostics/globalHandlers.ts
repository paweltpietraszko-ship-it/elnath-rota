// T021c section 3.3: window.onerror / unhandledrejection -> diagnostic
// events. Only code location and exception type are recorded, never
// the raw message (which could echo user-entered data in a bug).

import { recordEvent, newEventId, nowIso, getCurrentScreen } from "./buffer";

let installed = false;

export function installGlobalErrorHandlers() {
  if (installed) return;
  installed = true;

  window.addEventListener("error", (ev: ErrorEvent) => {
    recordEvent({
      event_id: newEventId(),
      timestamp: nowIso(),
      screen: getCurrentScreen(),
      kind: "UNHANDLED_ERROR",
      error_type: ev.error?.name || "Error",
      source_ref: `${ev.filename || "unknown"}:${ev.lineno ?? 0}:${ev.colno ?? 0}`,
    });
  });

  window.addEventListener("unhandledrejection", (ev: PromiseRejectionEvent) => {
    const reason = ev.reason as unknown;
    const errorType =
      reason instanceof Error ? reason.name : typeof reason === "string" ? "string" : typeof reason;
    recordEvent({
      event_id: newEventId(),
      timestamp: nowIso(),
      screen: getCurrentScreen(),
      kind: "UNHANDLED_REJECTION",
      error_type: errorType,
    });
  });
}
