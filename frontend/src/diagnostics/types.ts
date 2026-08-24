// T021c: shared shape for the frontend diagnostic event buffer.
// Every field here is either a code-controlled label/enum or a numeric
// timestamp/duration -- never a raw error message, form value, or URL
// query string. See tasks/ROTA-T021c/brief.md section 3.5.

export type DiagEventKind =
  | "CLICK_RECEIVED"
  | "REQUEST_STARTED"
  | "REQUEST_SUCCEEDED"
  | "REQUEST_FAILED"
  | "REQUEST_TIMEOUT"
  | "NAVIGATION"
  | "RENDER_ERROR"
  | "UNHANDLED_ERROR"
  | "UNHANDLED_REJECTION"
  | "ACTION_STALLED"
  | "ACTION_NOOP";

export interface DiagEventBase {
  event_id: string;
  timestamp: string; // UTC ISO
  screen: string;
  kind: DiagEventKind;
}

export interface ClickReceivedEvent extends DiagEventBase {
  kind: "CLICK_RECEIVED";
  action_id: string;
  action: string;
}

export interface RequestStartedEvent extends DiagEventBase {
  kind: "REQUEST_STARTED";
  action_id: string | null;
  method: string;
  endpoint_template: string;
}

export interface RequestSucceededEvent extends DiagEventBase {
  kind: "REQUEST_SUCCEEDED";
  action_id: string | null;
  method: string;
  endpoint_template: string;
  status: number;
  duration_ms: number;
}

export interface RequestFailedEvent extends DiagEventBase {
  kind: "REQUEST_FAILED";
  action_id: string | null;
  method: string;
  endpoint_template: string;
  status: number | null;
  error_category: "http_4xx" | "http_5xx" | "network" | "parse" | "unknown";
  duration_ms: number;
}

export interface RequestTimeoutEvent extends DiagEventBase {
  kind: "REQUEST_TIMEOUT";
  action_id: string | null;
  method: string;
  endpoint_template: string;
  duration_ms: number;
}

export interface NavigationEvent extends DiagEventBase {
  kind: "NAVIGATION";
  action_id: string | null;
  to_screen: string;
}

export interface RenderErrorEvent extends DiagEventBase {
  kind: "RENDER_ERROR";
  action_id: string | null; // R4 (round-4 audit): the resolving id, exported -- null when unavailable/ambiguous
  diagnostic_code: string;
  error_type: string;
  component_stack: string; // component display names only, no props/data
}

export interface UnhandledErrorEvent extends DiagEventBase {
  kind: "UNHANDLED_ERROR";
  action_id: string | null; // R4: same rule as RenderErrorEvent above
  error_type: string;
  source_ref: string; // "file:line:col", code location only
}

export interface UnhandledRejectionEvent extends DiagEventBase {
  kind: "UNHANDLED_REJECTION";
  action_id: string | null; // R4: same rule as RenderErrorEvent above
  error_type: string;
}

export interface ActionStalledEvent extends DiagEventBase {
  kind: "ACTION_STALLED";
  action_id: string;
  action: string;
}

export interface ActionNoopEvent extends DiagEventBase {
  kind: "ACTION_NOOP";
  action_id: string;
  action: string;
}

export type DiagEvent =
  | ClickReceivedEvent
  | RequestStartedEvent
  | RequestSucceededEvent
  | RequestFailedEvent
  | RequestTimeoutEvent
  | NavigationEvent
  | RenderErrorEvent
  | UnhandledErrorEvent
  | UnhandledRejectionEvent
  | ActionStalledEvent
  | ActionNoopEvent;

export interface FrontendDiagnosticReport {
  schema_version: 1;
  session_id: string;
  build_sha: string;
  generated_at: string;
  current_screen: string;
  events: DiagEvent[];
}
