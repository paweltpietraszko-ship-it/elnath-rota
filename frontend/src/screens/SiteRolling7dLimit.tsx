// ROTA-OCHRONA-EDIT-7D-LIMIT brief.md: OCHRONA-only button + small modal
// to edit the existing rolling_7d_decision_threshold_hours. Never rendered
// for ORDINARY (caller gates on planning_regime) -- the server refuses the
// write regardless, this is just keeping the control out of sight where it
// can never apply.
import { useState } from "react";
import { api } from "../api/client";

const WARNING_THRESHOLD_HOURS = 72;

export default function SiteRolling7dLimit({ siteId }: { siteId: string }) {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState<number | null>(null);
  const [value, setValue] = useState<string>("");
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openModal = () => {
    setOpen(true);
    setError(null);
    setConfirmed(false);
    setLoading(true);
    api
      .getRolling7dLimit(siteId)
      .then((r) => {
        setCurrent(r.rolling_7d_decision_threshold_hours);
        setValue(String(r.rolling_7d_decision_threshold_hours));
      })
      .catch((e) => setError(String((e as Error).message ?? e)))
      .finally(() => setLoading(false));
  };

  const parsed = Number(value);
  const valid = value !== "" && Number.isInteger(parsed) && parsed > 0;
  const overWarningThreshold = valid && parsed > WARNING_THRESHOLD_HOURS;

  const save = async () => {
    if (!valid || (overWarningThreshold && !confirmed)) return;
    setSaving(true);
    setError(null);
    try {
      await api.setRolling7dLimit(siteId, parsed, confirmed);
      setOpen(false);
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="panel">
      <h3>Limit obciążenia w ruchomych 7 dniach</h3>
      <p className="panel-hint">
        Bieżący próg{current !== null ? `: ${current} h` : ""}. Zmiana dotyczy tylko tego obiektu i nie przelicza już
        istniejącego grafiku.
      </p>
      <button className="btn-secondary" data-diag-action="rolling-7d-limit-open" onClick={openModal}>
        Zmień limit godzin
      </button>

      {open && (
        <div className="modal-backdrop" onClick={() => setOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Limit obciążenia w ruchomych 7 dniach</h2>
            {error && <div className="banner-error">{error}</div>}
            {loading ? (
              <p>Ładowanie…</p>
            ) : (
              <>
                <label>
                  <span className="field-label">Nowy limit godzin w ruchomych 7 dniach</span>
                  <input
                    type="number"
                    min={1}
                    value={value}
                    onChange={(e) => {
                      setValue(e.target.value);
                      setConfirmed(false);
                    }}
                  />
                </label>
                {overWarningThreshold && (
                  <div className="banner-warning" style={{ marginTop: 12 }}>
                    <p>
                      Uwaga: bardzo wysoki limit godzin. Ustawiasz próg obciążenia przekraczający 72 godziny w
                      ruchomych 7 dniach. Taka wartość może dopuścić grafik naruszający przepisy o czasie pracy i
                      odpoczynku. Koordynator musi sprawdzić zgodność grafiku z obowiązującymi zasadami.
                    </p>
                    <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <input
                        type="checkbox"
                        style={{ width: "auto" }}
                        checked={confirmed}
                        onChange={(e) => setConfirmed(e.target.checked)}
                      />
                      Rozumiem ostrzeżenie i potwierdzam zmianę
                    </label>
                  </div>
                )}
              </>
            )}
            <div className="modal-actions">
              <button className="btn-ghost" onClick={() => setOpen(false)}>
                Anuluj
              </button>
              <button
                className="btn-primary"
                onClick={save}
                disabled={saving || loading || !valid || (overWarningThreshold && !confirmed)}
              >
                {saving ? "Zapisywanie…" : "Zapisz"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
