import { useEffect, useState } from "react";
import Workspace from "./screens/Workspace";
import Room from "./screens/Room";
import "./App.css";
import { recordEvent, newEventId, nowIso, setCurrentScreen, getCurrentScreen } from "./diagnostics/buffer";
import { consumePendingActionId, resolveAction } from "./diagnostics/tracking";
import TestHooks from "./diagnostics/TestHooks";

export type View =
  | { screen: "workspace" }
  | { screen: "room"; siteId: string; siteName: string }
  | { screen: "employee"; siteId: string; siteName: string; employeeId: string };

function screenNameFor(view: View): string {
  return view.screen;
}

export default function App() {
  const [view, setView] = useState<View>({ screen: "workspace" });

  useEffect(() => {
    setCurrentScreen(screenNameFor(view));
  }, [view]);

  const navigate = (next: View) => {
    const fromScreen = getCurrentScreen();
    const actionId = consumePendingActionId();
    const toScreen = screenNameFor(next);
    setView(next);
    setCurrentScreen(toScreen);
    resolveAction(actionId);
    recordEvent({
      event_id: newEventId(),
      timestamp: nowIso(),
      screen: fromScreen,
      kind: "NAVIGATION",
      action_id: actionId,
      to_screen: toScreen,
    });
  };

  return (
    <>
      {view.screen === "workspace" ? (
        <Workspace onOpenSite={(siteId, siteName) => navigate({ screen: "room", siteId, siteName })} />
      ) : (
        <Room view={view} onNavigate={navigate} />
      )}
      {import.meta.env.DEV && <TestHooks />}
    </>
  );
}
