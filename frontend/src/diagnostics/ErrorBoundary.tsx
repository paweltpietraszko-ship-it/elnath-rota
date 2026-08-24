// T021c section 3.3: never a white screen. Catches a render crash,
// records RENDER_ERROR with a short code the user can quote, and offers
// a local-only diagnostic download plus a safe reload/back.

import { Component, ErrorInfo, ReactNode } from "react";
import { recordEvent, newEventId, nowIso, getCurrentScreen } from "./buffer";
import { downloadFrontendReport } from "./report";

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
    recordEvent({
      event_id: newEventId(),
      timestamp: nowIso(),
      screen: getCurrentScreen(),
      kind: "RENDER_ERROR",
      diagnostic_code: this.state.code ?? shortCode(),
      error_type: error?.name || "Error",
      component_stack: info.componentStack ?? "",
    });
  }

  render() {
    if (this.state.code) {
      return (
        <div style={{ padding: 40, maxWidth: 520, margin: "60px auto", fontFamily: "system-ui, sans-serif" }}>
          <h1 style={{ fontSize: 20, marginBottom: 8 }}>Coś poszło nie tak</h1>
          <p style={{ marginBottom: 4 }}>
            Aplikacja napotkała błąd i nie może pokazać tego ekranu. Kod diagnostyczny:{" "}
            <strong>{this.state.code}</strong>
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
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
