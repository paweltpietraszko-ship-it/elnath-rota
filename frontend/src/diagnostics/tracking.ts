// T021c section 3.1/3.2: one global, capture-phase click listener
// correlates a click with whatever happens next (request start,
// navigation, an observable DOM change, or a registered error). If
// none of those happen within STALLED_WINDOW_MS, the action is
// reported as ACTION_STALLED. This intentionally avoids instrumenting
// every button/handler individually -- "centralnie" per the brief.

import { recordEvent, newEventId, newActionId, nowIso, getCurrentScreen, findLastByActionId } from "./buffer";

const STALLED_WINDOW_MS = 800;
export const REQUEST_TIMEOUT_MS = 20000;

// Synchronous hand-off: a native click (capture phase, before React's
// synthetic dispatch) sets this; any fetch call issued synchronously
// within the resulting click handler (i.e. before its first await)
// reads it via consumePendingActionId(). Cleared on the next macrotask
// so a request started by an unrelated, later click never inherits it.
let pendingActionId: string | null = null;
let clearPendingTimer: ReturnType<typeof setTimeout> | null = null;

function setPendingActionId(id: string) {
  pendingActionId = id;
  if (clearPendingTimer) clearTimeout(clearPendingTimer);
  clearPendingTimer = setTimeout(() => {
    pendingActionId = null;
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

// R1-2A (round-1 audit): a registered window.error/unhandledrejection
// can be the causal effect of a click (e.g. it throws asynchronously,
// after pendingActionId has already been cleared for fetch-correlation
// purposes -- see setPendingActionId's comment). Unlike pendingActionId,
// this is NOT cleared after one macrotask: it stays "the most recent
// click" for the click's own stalled-detection window, so an error
// surfacing shortly after resolves the click that caused it instead of
// leaving it to fire a spurious ACTION_STALLED.
let mostRecentActionId: string | null = null;

export function resolveMostRecentAction() {
  resolveAction(mostRecentActionId);
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

// R1-2B (round-1 audit): watching document.body (or any ancestor of the
// React root) means an unrelated mutation elsewhere on the page -- an
// attribute set directly on <body>, a toast from a totally different
// component -- gets credited as "the effect" of this click, hiding a
// genuinely dead control. Scoping to the React mount point means only
// mutations React itself produced in response to being (re-)rendered
// can resolve a click; a change to <body> itself, outside that subtree,
// cannot.
function watchForMutation(actionId: string) {
  const root = document.getElementById("root");
  if (typeof MutationObserver === "undefined" || !root) return;
  const observer = new MutationObserver(() => {
    resolveAction(actionId);
    observer.disconnect();
  });
  observer.observe(root, { childList: true, subtree: true, attributes: true, characterData: true });
  // Stop watching once the stalled window has passed either way.
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
  mostRecentActionId = actionId;
  watchForMutation(actionId);

  setTimeout(() => {
    if (resolvedActionIds.has(actionId)) {
      resolvedActionIds.delete(actionId);
      return;
    }
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
