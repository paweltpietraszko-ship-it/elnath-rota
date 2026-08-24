import type { View } from "../App";
import ControlPanel from "./ControlPanel";
import EmployeeDetail from "./EmployeeDetail";

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

export default function Room({ view, onNavigate }: { view: View; onNavigate: (v: View) => void }) {
  if (view.screen === "workspace") return null;
  const { siteId, siteName } = view;

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
              {NAV_ITEMS.map((item) => (
                <button
                  key={item}
                  className={`nav-item${item === "Panel sterowania" ? " nav-item-active" : ""}`}
                  disabled={item !== "Panel sterowania"}
                  title={item !== "Panel sterowania" ? "jeszcze nie zbudowane" : undefined}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="room-content">
          <div className="room-content-inner">
            {view.screen === "room" && <ControlPanel siteId={siteId} siteName={siteName} onNavigate={onNavigate} />}
            {view.screen === "employee" && (
              <EmployeeDetail
                siteId={siteId}
                siteName={siteName}
                employeeId={view.employeeId}
                onBack={() => onNavigate({ screen: "room", siteId, siteName })}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
