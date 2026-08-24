// T021c section 3.1/3.2: one global, capture-phase click listener
// correlates a click with whatever happens next.
//
// R4 (owner ruling, round-3 audit aftermath): three rounds of trying to
// make EVERY async result path (arbitrarily delayed setTimeout/Promise
// chains) correlate back to its causing click, via progressively more
// elaborate timing/propagation tricks, foundered on a hard fact proven
// empirically: a single click's own capture/target/bubble dispatch is
// NOT one uninterrupted synchronous execution in this browser -- a
// microtask queued from the capture-phase listener can run BEFORE the
// same click's own target-phase listener. No fixed window, frame count,
// or global setTimeout/Promise wrapping can reliably outrun that, so
// the owner explicitly narrowed the diagnostic promise instead:
//
//   - every click is recorded (CLICK_RECEIVED), always;
//   - a request via req(), a navigation, and a DIRECT (synchronous)
//     render error are reliably tied to the click that caused them;
//   - window.error / unhandledrejection are ALWAYS recorded, but their
//     action_id is best-effort: attempted only via the same short,
//     macrotask-scoped window req() already uses (pendingActionId,
//     below), never guessed from "whichever click was most recent";
//   - ACTION_STALLED means "no confirmed reaction", not "confirmed no
//     reaction" -- it is a diagnostic hint, not a proof;
//   - an error whose origin can't be established stays uncorrelated
//     (action_id=null) rather than resolving an unrelated click;
//   - no monkey-patching of setTimeout/Promise/microtasks to chase
//     arbitrary async causality.

import { recordEvent, newEventId, newActionId, nowIso, getCurrentScreen, findLastByActionId } from "./buffer";

const STALLED_WINDOW_MS = 800;
export const REQUEST_TIMEOUT_MS = 20000;

// Synchronous-ish hand-off, proven reliable in practice (req() has used
// it without issue): a click (capture phase) sets this; consumers read
// it before the next macrotask clears it. Because the clear is itself a
// macrotask, it survives any microtask interleaving within the SAME
// click's own dispatch (capture/target/bubble), which is exactly the
// scope "reliably tied to this click" needs -- and exactly why a
// genuinely later, unrelated click never inherits a stale value.
let pendingActionId: string | null = null;
let clearPendingTimer: ReturnType<typeof setTimeout> | null = null;

function setPendingActionId(id: string) {
  pendingActionId = id;
  if (clearPendingTimer) clearTimeout(clearPendingTimer);
  // Two chained macrotasks, not one: the browser dispatches
  // unhandledrejection as its own queued task, itself scheduled after
  // the current task's microtask checkpoint -- empirically, that task
  // lands in the queue AFTER a setTimeout(0) scheduled earlier in the
  // same click (verified directly; a single-macrotask clear cleared
  // this before a synchronous Promise.reject()'s own unhandledrejection
  // ever fired). One extra queue turn is still far short of any
  // subsequent, genuinely unrelated click or task.
  clearPendingTimer = setTimeout(() => {
    clearPendingTimer = setTimeout(() => {
      pendingActionId = null;
    }, 0);
  }, 0);
}

export function consumePendingActionId(): string | null {
  return pendingActionId;
}

const resolvedActionIds = new Set<string>();

export function resolveAction(actionId: string | null | undefined) {
  if (!actionId) return;
  resolvedActionIds.add(actionId);
}

function isInteractiveControl(el: Element): boolean {
  const tag = el.tagName.toLowerCase();
  if (tag === "button" || tag === "a" || tag === "select") return true;
  if (tag === "input") {
    const type = (el as HTMLInputElement).type;
    return type === "checkbox" || type === "radio" || type === "submit" || type === "button";
  }
  const role = el.getAttribute("role");
  return role === "button" || role === "link";
}

function findInteractiveAncestor(target: EventTarget | null): Element | null {
  let el = target instanceof Element ? target : null;
  let depth = 0;
  while (el && depth < 6) {
    if (isInteractiveControl(el)) return el;
    el = el.parentElement;
    depth++;
  }
  return null;
}

// Action names are never derived from element text/aria-label content --
// those can carry PII (e.g. an employee's display name inside a link).
// Only an explicit, developer-authored data-diag-action tag or a safe,
// generic tag+type fallback is ever recorded.
function actionNameFor(el: Element): string {
  const tagged = el.getAttribute("data-diag-action");
  if (tagged) return tagged;
  const tag = el.tagName.toLowerCase();
  if (tag === "input") {
    const type = (el as HTMLInputElement).type || "text";
    return `input:${type}:untagged`;
  }
  return `${tag}:untagged`;
}

// Best-effort UI-effect detection (brief.md section 3.2's "obserwowalna
// zmiana UI"): watches #root for the declared stalled window and
// resolves on any mutation observed there. Deliberately simple -- per
// the R4 owner ruling this is a best-effort signal, not a guarantee, so
// it does not attempt precise causal scoping (which is exactly what
// three rounds of increasingly elaborate attempts showed isn't
// reliably buildable here).
function watchForMutation(actionId: string) {
  const root = document.getElementById("root");
  if (typeof MutationObserver === "undefined" || !root) return;
  const observer = new MutationObserver(() => {
    resolveAction(actionId);
    observer.disconnect();
  });
  observer.observe(root, { childList: true, subtree: true, attributes: true, characterData: true });
  setTimeout(() => observer.disconnect(), STALLED_WINDOW_MS);
}

function onCapturedClick(ev: MouseEvent) {
  const control = findInteractiveAncestor(ev.target);
  if (!control) return;
  if (control.hasAttribute("disabled")) return;

  const actionId = newActionId();
  const action = actionNameFor(control);
  const screen = getCurrentScreen();

  recordEvent({
    event_id: newEventId(),
    timestamp: nowIso(),
    screen,
    kind: "CLICK_RECEIVED",
    action_id: actionId,
    action,
  });

  setPendingActionId(actionId);
  watchForMutation(actionId);

  setTimeout(() => {
    if (resolvedActionIds.has(actionId)) {
      resolvedActionIds.delete(actionId);
      return;
    }
    // "No confirmed reaction" (R4 owner ruling), not a proof nothing
    // happened -- a delayed effect this mechanism cannot reliably trace
    // may still land after this point.
    recordEvent({
      event_id: newEventId(),
      timestamp: nowIso(),
      screen,
      kind: "ACTION_STALLED",
      action_id: actionId,
      action,
    });
  }, STALLED_WINDOW_MS);
}

let installed = false;

export function installClickTracking() {
  if (installed) return;
  installed = true;
  document.addEventListener("click", onCapturedClick, true);
}

export function recordNoop(actionId: string, action: string) {
  resolveAction(actionId);
  recordEvent({
    event_id: newEventId(),
    timestamp: nowIso(),
    screen: getCurrentScreen(),
    kind: "ACTION_NOOP",
    action_id: actionId,
    action,
  });
}

export function findEventByActionId(actionId: string) {
  return findLastByActionId(actionId);
}
