// T021c section 3.1: single shared registry for the frontend diagnostic
// event buffer. Ring-buffered, capped, sessionStorage-backed so it
// survives a reload after a crash (brief.md section 3.1/3.3) without
// becoming a full activity log.

import type { DiagEvent, FrontendDiagnosticReport } from "./types";

const MAX_EVENTS = 300;
const STORAGE_KEY = "elnath-rota-diag-buffer";
const SESSION_KEY = "elnath-rota-diag-session-id";

function randomId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
}

function readSessionId(): string {
  try {
    const existing = sessionStorage.getItem(SESSION_KEY);
    if (existing) return existing;
    const id = randomId();
    sessionStorage.setItem(SESSION_KEY, id);
    return id;
  } catch {
    return randomId();
  }
}

function loadPersisted(): DiagEvent[] {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function persist() {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(events));
  } catch {
    // per-viewer diagnostic convenience only; ignore storage failures
  }
}

export const sessionId = readSessionId();
export const buildSha: string =
  typeof __BUILD_SHA__ === "string" && __BUILD_SHA__ ? __BUILD_SHA__ : "unknown";

let events: DiagEvent[] = loadPersisted();
let currentScreen = "unknown";

export function setCurrentScreen(screen: string) {
  currentScreen = screen;
}

export function getCurrentScreen(): string {
  return currentScreen;
}

export function recordEvent(event: DiagEvent) {
  events.push(event);
  if (events.length > MAX_EVENTS) {
    events = events.slice(events.length - MAX_EVENTS);
  }
  persist();
}

export function findLastByActionId(actionId: string): DiagEvent | undefined {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i] as DiagEvent & { action_id?: string | null };
    if (e.action_id === actionId) return events[i];
  }
  return undefined;
}

export function getEvents(): readonly DiagEvent[] {
  return events;
}

export function buildReport(): FrontendDiagnosticReport {
  return {
    schema_version: 1,
    session_id: sessionId,
    build_sha: buildSha,
    generated_at: new Date().toISOString(),
    current_screen: currentScreen,
    events: [...events],
  };
}

export function newEventId(): string {
  return randomId();
}

export function newActionId(): string {
  return randomId();
}

export function nowIso(): string {
  return new Date().toISOString();
}
