// T021c section 3.3: never a white screen. Catches a render crash,
// records RENDER_ERROR with a short code the user can quote, and offers
// a local-only diagnostic download plus a safe reload/back.

import { Component, ErrorInfo, ReactNode } from "react";
import { recordEvent, newEventId, nowIso, getCurrentScreen } from "./buffer";
import { downloadFrontendReport } from "./report";
import { resolveAction, consumePendingActionId } from "./tracking";
import { TECHNICAL_ERROR_MESSAGE } from "../api/client";

function shortCode(): string {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let out = "";
  for (let i = 0; i < 6; i++) out += chars[Math.floor(Math.random() * chars.length)];
  return out;
}

interface State {
  code: string | null;
}

export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { code: null };

  static getDerivedStateFromError(): State {
    return { code: shortCode() };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // A direct (synchronous) render crash from a click's own update is
    // reliably tied to it via pendingActionId, same as req() (R4 owner
    // ruling: this is one of the correlations kept, unlike arbitrarily
    // delayed work). Read once, export it, and resolve with that exact
    // same value (round-4 audit: the internal resolution must be
    // visible in the exported event, not just used internally).
    const actionId = consumePendingActionId();
    recordEvent({
      event_id: newEventId(),
      timestamp: nowIso(),
      screen: getCurrentScreen(),
      kind: "RENDER_ERROR",
      action_id: actionId,
      diagnostic_code: this.state.code ?? shortCode(),
      error_type: error?.name || "Error",
      component_stack: info.componentStack ?? "",
    });
    resolveAction(actionId);
  }

  render() {
    if (this.state.code) {
      return (
        <div style={{ padding: 40, maxWidth: 520, margin: "60px auto", fontFamily: "system-ui, sans-serif" }}>
          <h1 style={{ fontSize: 20, marginBottom: 8 }}>Coś poszło nie tak</h1>
          {/* ROTA-TECHNICAL-ERROR-RECOVERY-UX (brief.md section 6, Codex
              R3-03 on 05f2e2a): the one frozen technical-error sentence,
              same surface as any other backend/network failure -- this
              boundary keeps its own diagnostic code (a render crash has
              richer, code-addressable frontend diagnostics the generic
              message alone would lose) and reuse/back/refresh actions,
              never a second ErrorBoundary. */}
          <p style={{ marginBottom: 4 }}>{TECHNICAL_ERROR_MESSAGE}</p>
          <p style={{ marginBottom: 4 }}>
            Kod diagnostyczny: <strong>{this.state.code}</strong>
          </p>
          <p style={{ marginBottom: 20, color: "#666", fontSize: 13 }}>
            Ten kod pozwala odnaleźć zdarzenie w raporcie diagnostycznym — nie trzeba przepisywać treści błędu.
          </p>
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={() => downloadFrontendReport()}>Pobierz diagnostykę frontu</button>
            <button onClick={() => window.location.reload()}>Odśwież</button>
            <button
              onClick={() => {
                window.location.href = "/";
              }}
            >
              Wróć do startu
            </button>
            <button disabled title="Wsparcie techniczne niedostępne w tej wersji">
              Kontakt ze wsparciem
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
