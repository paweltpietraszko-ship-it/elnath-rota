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
// Deliberately separate from activeClickContext below: this one must
// decay fast so a later, non-click-triggered request (e.g. a mount
// effect) never inherits a stale click's id.
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

// R2 (round-2 audit): a "most recent click wins" heuristic misattributes
// a delayed error to whichever click happened to occur later, even when
// that later click never scheduled the failing work. Real causal
// tracking instead: every click gets its own causal context
// (activeClickContext), and any setTimeout SCHEDULED WHILE that context
// is active is wrapped so the SAME context is restored when it finally
// fires -- regardless of what any other, unrelated click has done to
// the global "current" click in the meantime. A later click simply
// never touches an earlier click's already-captured closure.
let activeClickContext: string | null = null;

// If the wrapped callback throws, execution never reaches the
// "restore previous" line below, so activeClickContext is left exactly
// as the throwing callback's own context -- available for the error
// listener (which runs synchronously as the exception unwinds to the
// top) to read. The listener itself resets it afterwards.
function withClickContext<T>(id: string | null, fn: () => T): T {
  const previous = activeClickContext;
  activeClickContext = id;
  const result = fn();
  activeClickContext = previous;
  return result;
}

let timerPropagationInstalled = false;

function installTimerContextPropagation() {
  if (timerPropagationInstalled || typeof window === "undefined") return;
  timerPropagationInstalled = true;
  const nativeSetTimeout = window.setTimeout.bind(window);
  window.setTimeout = ((handler: TimerHandler, timeout?: number, ...args: unknown[]) => {
    if (typeof handler !== "function") {
      return nativeSetTimeout(handler as unknown as () => void, timeout, ...args);
    }
    const capturedContext = activeClickContext;
    const wrapped = () => withClickContext(capturedContext, () => (handler as (...a: unknown[]) => unknown)(...args));
    return nativeSetTimeout(wrapped, timeout);
  }) as typeof window.setTimeout;
}

export function resolveActiveClickContext() {
  resolveAction(activeClickContext);
  activeClickContext = null;
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

// R2 (round-2 audit): watching the whole #root subtree for the full
// STALLED_WINDOW_MS meant ANY later, unrelated re-render anywhere in
// the app (a different component's own effect, a background refresh)
// got credited to this click. A real UI effect from a click handler
// commits synchronously and paints within the next couple of frames;
// scoping the watch to that short window instead of the full stall
// window means a mutation arriving well after (as in the audit's 100ms
// repro) is no longer in scope to misattribute.
const MUTATION_ATTRIBUTION_FRAMES = 2;

function watchForMutation(actionId: string) {
  const root = document.getElementById("root");
  if (typeof MutationObserver === "undefined" || !root) return;
  const observer = new MutationObserver(() => {
    resolveAction(actionId);
    observer.disconnect();
  });
  observer.observe(root, { childList: true, subtree: true, attributes: true, characterData: true });

  let framesLeft = MUTATION_ATTRIBUTION_FRAMES;
  const tick = () => {
    framesLeft -= 1;
    if (framesLeft <= 0) {
      observer.disconnect();
      return;
    }
    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(tick);
    } else {
      observer.disconnect();
    }
  };
  if (typeof requestAnimationFrame === "function") {
    requestAnimationFrame(tick);
  } else {
    // No rAF (non-browser test runner): fall back to a short timer.
    setTimeout(() => observer.disconnect(), 50);
  }
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
  activeClickContext = actionId;
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
  installTimerContextPropagation();
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
