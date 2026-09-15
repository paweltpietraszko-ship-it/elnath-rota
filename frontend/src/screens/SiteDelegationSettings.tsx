// ROTA-DELEGACJA-ABSENCE-KIND brief.md section 4/11: one small, self-
// contained section on Panel sterowania -> Obiekt, same pattern as
// PrintSettings.tsx -- fetches and saves this Site's own current default
// via the one narrow delegation-default-hours resource. Never a full CRUD
// screen, never touched by an existing schedule.
import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function SiteDelegationSettings({ siteId }: { siteId: string }) {
  const [value, setValue] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const load = () => {
    setLoading(true);
    api
      .getDelegationDefaultHours(siteId)
      .then((r) => setValue(r.delegation_default_hours != null ? String(r.delegation_default_hours) : ""))
      .catch((e) => setError(String((e as Error).message ?? e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [siteId]);

  const parsed = Number(value);
  const valid = value !== "" && Number.isInteger(parsed) && parsed > 0;

  const save = async () => {
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      await api.setDelegationDefaultHours(siteId, parsed);
      setSavedAt(Date.now());
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="panel">
      <h3>Domyślne godziny delegacji</h3>
      <p className="panel-hint">
        Podpowiedź przy zgłaszaniu nowej delegacji pracownikowi tego obiektu — koordynator może ją zmienić dla
        konkretnego przypadku. Zmiana tej wartości nie dotyka już zapisanych delegacji.
      </p>
      {error && <div className="banner-error">{error}</div>}
      {loading ? (
        <p>Ładowanie…</p>
      ) : (
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
          <label style={{ maxWidth: 200 }}>
            <span className="field-label">Godziny dziennie</span>
            <input type="number" min={1} value={value} onChange={(e) => setValue(e.target.value)} />
          </label>
          <button className="btn-primary" onClick={save} disabled={saving || !valid}>
            {saving ? "Zapisywanie…" : "Zapisz"}
          </button>
          {savedAt && <span style={{ color: "var(--ink-faint)", fontSize: 12 }}>Zapisano.</span>}
        </div>
      )}
    </div>
  );
}
