import { useState } from "react";
import type { View } from "../App";
import Analytics from "./Analytics";
import ControlPanel from "./ControlPanel";
import EmployeeDetail from "./EmployeeDetail";
import MonthlyPlanning from "./MonthlyPlanning";

const NAV_ITEMS = [
  "Przegląd",
  "Panel sterowania",
  "Planowanie miesiąca",
  "Decyzje koordynatora",
  "Ręczna korekta",
  "Historia i audyt",
  "Analityka i bilanse",
  "Wydruk Grafiku",
];

const BUILT_NAV_ITEMS = new Set(["Panel sterowania", "Planowanie miesiąca", "Analityka i bilanse"]);
const NAV_DIAG_ACTIONS: Record<string, string> = {
  "Panel sterowania": "room-nav-control-panel",
  "Planowanie miesiąca": "room-nav-monthly-planning",
  "Analityka i bilanse": "room-nav-analytics",
};

type BuiltNavItem = "Panel sterowania" | "Planowanie miesiąca" | "Analityka i bilanse";

export default function Room({ view, onNavigate }: { view: View; onNavigate: (v: View) => void }) {
  const [activeNav, setActiveNav] = useState<BuiltNavItem>("Panel sterowania");
  if (view.screen === "workspace") return null;
  const { siteId, siteName } = view;

  const selectNav = (item: string) => {
    if (!BUILT_NAV_ITEMS.has(item)) return;
    setActiveNav(item as BuiltNavItem);
    if (view.screen === "employee") onNavigate({ screen: "room", siteId, siteName });
  };

  return (
    <div className="room">
      <div className="room-topbar">
        <div className="topbar-brand">
          <div className="topbar-brand-mark">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M12 2v6M12 16v6M2 12h6M16 12h6" />
            </svg>
          </div>
          <span className="brand-font topbar-brand-name">Elnath Rota</span>
        </div>
        <div className="room-breadcrumb">
          <button className="room-breadcrumb-back" data-diag-action="breadcrumb-back" onClick={() => onNavigate({ screen: "workspace" })}>
            ← Twoje obiekty
          </button>
          <span className="room-breadcrumb-sep">/</span>
          <span className="room-breadcrumb-current">{siteName}</span>
        </div>
        <div />
      </div>

      <div className="room-body">
        <div className="room-sidebar">
          <div>
            <p className="room-sidebar-label">Ekrany</p>
            <div className="room-sidebar-nav">
              {NAV_ITEMS.map((item) => {
                const built = BUILT_NAV_ITEMS.has(item);
                return (
                  <button
                    key={item}
                    className={`nav-item${built && item === activeNav ? " nav-item-active" : ""}`}
                    disabled={!built}
                    title={!built ? "jeszcze nie zbudowane" : undefined}
                    data-diag-action={NAV_DIAG_ACTIONS[item]}
                    onClick={() => selectNav(item)}
                  >
                    {item}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="room-content">
          <div className="room-content-inner">
            {activeNav === "Panel sterowania" && view.screen === "room" && (
              <ControlPanel siteId={siteId} siteName={siteName} onNavigate={onNavigate} />
            )}
            {activeNav === "Panel sterowania" && view.screen === "employee" && (
              <EmployeeDetail
                siteId={siteId}
                siteName={siteName}
                employeeId={view.employeeId}
                onBack={() => onNavigate({ screen: "room", siteId, siteName })}
              />
            )}
            {activeNav === "Planowanie miesiąca" && <MonthlyPlanning siteId={siteId} />}
            {activeNav === "Analityka i bilanse" && <Analytics siteId={siteId} />}
          </div>
        </div>
      </div>
    </div>
  );
}
