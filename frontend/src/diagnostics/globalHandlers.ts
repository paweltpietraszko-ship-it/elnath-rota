// T021c section 3.3: window.onerror / unhandledrejection -> diagnostic
// events. Only code location and exception type are recorded, never
// the raw message (which could echo user-entered data in a bug).
//
// R4 (owner ruling): these are ALWAYS recorded, but action_id
// correlation is best-effort -- read via the same short,
// macrotask-scoped window req() uses (pendingActionId), never guessed
// from "whichever click happened most recently". For arbitrarily
// delayed work this often resolves to null, and that is correct: an
// error whose origin can't be established must stay uncorrelated
// rather than resolve an unrelated click.

import { recordEvent, newEventId, nowIso, getCurrentScreen } from "./buffer";
import { resolveAction, consumePendingActionId } from "./tracking";

let installed = false;

export function installGlobalErrorHandlers() {
  if (installed) return;
  installed = true;

  window.addEventListener("error", (ev: ErrorEvent) => {
    const actionId = consumePendingActionId();
    recordEvent({
      event_id: newEventId(),
      timestamp: nowIso(),
      screen: getCurrentScreen(),
      kind: "UNHANDLED_ERROR",
      error_type: ev.error?.name || "Error",
      source_ref: `${ev.filename || "unknown"}:${ev.lineno ?? 0}:${ev.colno ?? 0}`,
    });
    resolveAction(actionId);
  });

  window.addEventListener("unhandledrejection", (ev: PromiseRejectionEvent) => {
    const actionId = consumePendingActionId();
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
    resolveAction(actionId);
  });
}
