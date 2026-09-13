import { useEffect, useState } from "react";
import Workspace from "./screens/Workspace";
import Room from "./screens/Room";
import Login from "./screens/Login";
import "./App.css";
import { recordEvent, newEventId, nowIso, setCurrentScreen, getCurrentScreen } from "./diagnostics/buffer";
import { consumePendingActionId, resolveAction } from "./diagnostics/tracking";
import TestHooks from "./diagnostics/TestHooks";
import { authApi } from "./api/client";

export type View =
  | { screen: "workspace" }
  | { screen: "room"; siteId: string; siteName: string }
  | { screen: "employee"; siteId: string; siteName: string; employeeId: string };

function screenNameFor(view: View): string {
  return view.screen;
}

export default function App() {
  const [view, setView] = useState<View>({ screen: "workspace" });
  // ROTA-T024-TESTER-LOGIN-ISOLATION (brief.md section 10): LOCAL_WINDOWS
  // has no auth surface at all (__CENTRAL_SERVICE__ false at build time),
  // so it starts "authenticated" and never shows a login screen.
  const [authState, setAuthState] = useState<"checking" | "loggedOut" | "loggedIn">(
    __CENTRAL_SERVICE__ ? "checking" : "loggedIn",
  );

  useEffect(() => {
    if (!__CENTRAL_SERVICE__) return;
    authApi
      .getCurrentUser()
      .then(() => setAuthState("loggedIn"))
      .catch(() => setAuthState("loggedOut"));
  }, []);

  useEffect(() => {
    if (!__CENTRAL_SERVICE__) return undefined;
    // brief.md T24-7: any 401 on a protected endpoint (session expired/
    // missing) sends the app back to the login screen.
    const onUnauthorized = () => setAuthState("loggedOut");
    window.addEventListener("rota:unauthorized", onUnauthorized);
    return () => window.removeEventListener("rota:unauthorized", onUnauthorized);
  }, []);

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

  if (authState === "checking") {
    return null;
  }

  if (authState === "loggedOut") {
    return <Login onLoggedIn={() => setAuthState("loggedIn")} />;
  }

  return (
    <>
      {view.screen === "workspace" ? (
        <Workspace onOpenSite={(siteId, siteName) => navigate({ screen: "room", siteId, siteName })} />
      ) : (
        <Room view={view} onNavigate={navigate} />
      )}
      {__E2E_TEST_HOOKS__ && <TestHooks />}
    </>
  );
}
