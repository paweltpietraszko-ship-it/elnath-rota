// T021c section 3.3: window.onerror / unhandledrejection -> diagnostic
// events. Only code location and exception type are recorded, never
// the raw message (which could echo user-entered data in a bug).

import { recordEvent, newEventId, nowIso, getCurrentScreen } from "./buffer";
import { resolveActiveClickContext } from "./tracking";

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
    // R1-2A: a registered error is an allowed resolution of the click
    // that caused it (brief.md section 3.2) -- must not also stall.
    resolveActiveClickContext();
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
    resolveActiveClickContext();
  });
}
