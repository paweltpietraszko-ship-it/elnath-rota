import { useState } from "react";
import Workspace from "./screens/Workspace";
import Room from "./screens/Room";
import "./App.css";

export type View =
  | { screen: "workspace" }
  | { screen: "room"; siteId: string; siteName: string }
  | { screen: "employee"; siteId: string; siteName: string; employeeId: string };

export default function App() {
  const [view, setView] = useState<View>({ screen: "workspace" });

  if (view.screen === "workspace") {
    return <Workspace onOpenSite={(siteId, siteName) => setView({ screen: "room", siteId, siteName })} />;
  }
  return <Room view={view} onNavigate={setView} />;
}
