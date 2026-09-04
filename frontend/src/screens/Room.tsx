import { useEffect, useState } from "react";
import type { View } from "../App";
import Analytics from "./Analytics";
import ControlPanel from "./ControlPanel";
import Decisions from "./Decisions";
import EmployeeDetail from "./EmployeeDetail";
import History from "./History";
import MonthlyPlanning from "./MonthlyPlanning";
import Overview from "./Overview";
import { todayYearMonth } from "../localDate";

const WORKING_MONTH_STORAGE_KEY = "elnath-rota-working-month";
// R3-01 (round-3 audit): "2026-99" has the right shape but no such month --
// the regex only checks the text shape, so also range-check the month 01-12.
const YEAR_MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/;

// ROTA-T053: one working month shared across MonthlyPlanning, Analytics,
// EmployeeDetail and the print flow (Export, embedded in MonthlyPlanning) --
// "Decyzje koordynatora" is a deliberate exception, it keeps its own list of
// months with pending decisions (brief §2 point 5).
function loadStoredWorkingMonth(): string {
  try {
    const stored = localStorage.getItem(WORKING_MONTH_STORAGE_KEY);
    if (stored && YEAR_MONTH_RE.test(stored)) return stored;
  } catch {
    // fail-soft to current month, see T53-08
  }
  return todayYearMonth();
}

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

const BUILT_NAV_ITEMS = new Set([
  "Przegląd", "Panel sterowania", "Planowanie miesiąca", "Decyzje koordynatora", "Ręczna korekta",
  "Historia i audyt", "Analityka i bilanse", "Wydruk Grafiku",
]);
const NAV_DIAG_ACTIONS: Record<string, string> = {
  "Przegląd": "room-nav-overview",
  "Panel sterowania": "room-nav-control-panel",
  "Planowanie miesiąca": "room-nav-monthly-planning",
  "Decyzje koordynatora": "room-nav-decisions",
  "Ręczna korekta": "room-nav-manual-correction",
  "Analityka i bilanse": "room-nav-analytics",
  "Historia i audyt": "room-nav-history",
  "Wydruk Grafiku": "room-nav-export",
};

// ROTA-T037 owner ruling (2026-08-28): Reczna korekta and Wydruk are NOT
// separate screens with their own logic -- they are the same content
// embedded inside Planowanie miesiaca (see MonthlyPlanning.tsx), reachable
// here only as a duplicate shortcut into that one screen.
type BuiltNavItem =
  | "Przegląd"
  | "Panel sterowania"
  | "Planowanie miesiąca"
  | "Decyzje koordynatora"
  | "Ręczna korekta"
  | "Analityka i bilanse"
  | "Historia i audyt"
  | "Wydruk Grafiku";

export default function Room({ view, onNavigate }: { view: View; onNavigate: (v: View) => void }) {
  const [activeNav, setActiveNav] = useState<BuiltNavItem>("Przegląd");
  // Set by Decyzje koordynatora/Wydruk Grafiku when they navigate into Panel
  // sterowania on a specific tab -- ControlPanel only reads this as its
  // initial tab on mount, see ControlPanel's own initialTab prop docs.
  const [controlPanelTab, setControlPanelTab] = useState<"obsada" | "obiekt">("obsada");
  // ROTA-T021 UI audit gate finding #4: no write path in the app threads
  // responds_to_decision_required_id yet (verified: no existing frontend
  // write call passes it) -- rather than inventing that plumbing for one
  // screen, this carries just enough context to show the coordinator WHICH
  // decision they're resolving on whichever screen they land on.
  const [decisionContext, setDecisionContext] = useState<{ decisionRequiredId: string; month: string } | null>(null);
  const [workingMonth, setWorkingMonth] = useState<string>(loadStoredWorkingMonth);

  useEffect(() => {
    try {
      localStorage.setItem(WORKING_MONTH_STORAGE_KEY, workingMonth);
    } catch {
      // per-viewer convenience only; ignore storage failures
    }
  }, [workingMonth]);

  if (view.screen === "workspace") return null;
  const { siteId, siteName } = view;

  const openControlPanel = (tab: "obsada" | "obiekt", context: { decisionRequiredId: string; month: string } | null = null) => {
    setControlPanelTab(tab);
    setDecisionContext(context);
    setActiveNav("Panel sterowania");
  };

  const selectNav = (item: string) => {
    if (!BUILT_NAV_ITEMS.has(item)) return;
    setActiveNav(item as BuiltNavItem);
    if (item !== "Panel sterowania") setDecisionContext(null);
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
        <label className="room-working-month" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="field-label">Miesiąc roboczy</span>
          <input
            type="month"
            value={workingMonth}
            data-diag-element="room-working-month"
            onChange={(e) => setWorkingMonth(e.target.value)}
          />
        </label>
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
            {activeNav === "Przegląd" && (
              <Overview
                siteId={siteId}
                onOpenControlPanel={() => openControlPanel("obsada")}
                onOpenPlanning={() => setActiveNav("Planowanie miesiąca")}
                onOpenDecisions={() => setActiveNav("Decyzje koordynatora")}
                onOpenExport={() => setActiveNav("Wydruk Grafiku")}
              />
            )}
            {activeNav === "Panel sterowania" && view.screen === "room" && (
              <ControlPanel
                siteId={siteId} siteName={siteName} onNavigate={onNavigate}
                initialTab={controlPanelTab} decisionContext={decisionContext}
              />
            )}
            {activeNav === "Panel sterowania" && view.screen === "employee" && (
              <EmployeeDetail
                siteId={siteId}
                siteName={siteName}
                employeeId={view.employeeId}
                onBack={() => onNavigate({ screen: "room", siteId, siteName })}
                respondsToDecisionRequiredId={decisionContext?.decisionRequiredId ?? null}
                workingMonth={workingMonth}
              />
            )}
            {/* ROTA-T041 OWNER-T041-04: all three shortcuts are one screen,
                one MonthlyPlanning instance (kept mounted across them so the
                selected object/month doesn't reset) -- entryMode only picks
                what's shown by default on arrival. */}
            {(activeNav === "Planowanie miesiąca" ||
              activeNav === "Ręczna korekta" ||
              activeNav === "Wydruk Grafiku") && (
              <MonthlyPlanning
                siteId={siteId}
                onOpenPrintSettings={() => openControlPanel("obiekt")}
                entryMode={
                  activeNav === "Ręczna korekta" ? "korekta" : activeNav === "Wydruk Grafiku" ? "wydruk" : undefined
                }
                workingMonth={workingMonth}
              />
            )}
            {activeNav === "Decyzje koordynatora" && (
              <Decisions siteId={siteId} onOpenControlPanel={(tab, context) => openControlPanel(tab, context)} />
            )}
            {activeNav === "Analityka i bilanse" && <Analytics siteId={siteId} workingMonth={workingMonth} />}
            {activeNav === "Historia i audyt" && <History siteId={siteId} />}
          </div>
        </div>
      </div>
    </div>
  );
}
