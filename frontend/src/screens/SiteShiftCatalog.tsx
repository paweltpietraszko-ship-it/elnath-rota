// ROTA-T030 (tasks/ROTA-T030/brief.md): Panel sterowania -> Obiekt. Local
// draft over the whole shift catalog, one atomic PUT via the existing
// req() client -- no direct fetch, no second diagnostic path.
import { useEffect, useState } from "react";
import { api, ShiftRowOut, SiteRoleOut } from "../api/client";

const WEEKDAY_NAMES = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Nd"];
const HOUR_OPTIONS = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, "0")}:00`);

interface DraftRow {
  key: string;
  kind: "D" | "N";
  start_time: string;
  end_time: string;
  required_primary_count: number;
  active_weekdays: number[];
  // ROTA-T065-CONFIGURABLE-ROLES section 5: "" is a draft-only transient
  // state (a brand new row before the coordinator picks a role) -- save()
  // rejects it client-side for ORDINARY before ever reaching the server,
  // since "— brak —" no longer exists as a real business option.
  required_role_id: string;
}

function newKey(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
}

function newRoleId(): string {
  try {
    return `ROLE-${crypto.randomUUID()}`;
  } catch {
    return `ROLE-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
}

// Mirrors api/routers/site_profile.py's own end_next_day/duration rule
// (end<=start spans into the next day; equal times are a full 24h shift)
// -- display-only preview, the server is still the source of truth.
function durationHours(start: string, end: string): number {
  const startHour = Number(start.slice(0, 2));
  const endHour = Number(end.slice(0, 2));
  let diff = endHour - startHour;
  if (diff <= 0) diff += 24;
  return diff;
}

function catalogKindLabel(hours: number): string {
  if (hours === 12) return "12h";
  if (hours === 24) return "24h";
  return "INNY";
}

function fromServer(rows: ShiftRowOut[]): DraftRow[] {
  return rows.map((r) => ({
    key: newKey(),
    kind: r.kind,
    start_time: r.start_time,
    end_time: r.end_time,
    required_primary_count: r.required_primary_count,
    active_weekdays: r.active_weekdays,
    required_role_id: r.required_role_id ?? "",
  }));
}

function blankRow(): DraftRow {
  return {
    key: newKey(), kind: "D", start_time: "06:00", end_time: "18:00",
    required_primary_count: 1, active_weekdays: [1, 2, 3, 4, 5, 6, 7], required_role_id: "",
  };
}

function RoleCatalogPanel({ siteId, roles, onChanged }: { siteId: string; roles: SiteRoleOut[]; onChanged: () => void }) {
  const [newName, setNewName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addRole = async () => {
    const displayName = newName.trim();
    if (!displayName) return;
    setSaving(true);
    setError(null);
    try {
      const roleId = newRoleId();
      await api.saveSiteRole(siteId, roleId, { role_id: roleId, display_name: displayName, active: true });
      setNewName("");
      onChanged();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSaving(false);
    }
  };

  const rename = async (role: SiteRoleOut, displayName: string) => {
    if (!displayName.trim() || displayName === role.display_name) return;
    try {
      await api.saveSiteRole(siteId, role.role_id, { role_id: role.role_id, display_name: displayName.trim(), active: role.active });
      onChanged();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  const toggleActive = async (role: SiteRoleOut) => {
    try {
      await api.saveSiteRole(siteId, role.role_id, { role_id: role.role_id, display_name: role.display_name, active: !role.active });
      onChanged();
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    }
  };

  return (
    <div className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Katalog ról</h3>
          <p className="panel-hint">
            Stanowiska właściwe dla tego obiektu (np. Kierownik, Sprzedawca — dla innej branży zupełnie inne nazwy).
            Wycofana rola znika z wyboru przy nowych zmianach, ale nie zmienia już zapisanej historii.
          </p>
        </div>
      </div>

      {error && <div className="banner-error">{error}</div>}

      {roles.length === 0 && (
        <p className="panel-hint" style={{ marginBottom: 10 }}>
          Brak ról — dodaj pierwszą, żeby móc wymagać roli w Katalogu zmian poniżej.
        </p>
      )}

      {roles.map((role) => (
        <div key={role.role_id} className="field-row" style={{ marginBottom: 8 }}>
          <input defaultValue={role.display_name} onBlur={(e) => rename(role, e.target.value)} disabled={!role.active} style={{ maxWidth: 240 }} />
          <button className="btn-ghost" data-diag-action="site-role-toggle-active" onClick={() => toggleActive(role)}>
            {role.active ? "Wycofaj" : "Przywróć"}
          </button>
        </div>
      ))}

      <div className="create-panel-fields" style={{ gridTemplateColumns: "1fr auto", marginTop: 10 }}>
        <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="np. Magazynier" />
        <button className="btn-primary" data-diag-action="site-role-add" onClick={addRole} disabled={saving || !newName.trim()}>
          + Dodaj rolę
        </button>
      </div>
    </div>
  );
}

export default function SiteShiftCatalog({
  siteId,
  respondsToDecisionRequiredId = null,
  onRolesChanged,
}: {
  siteId: string;
  // ROTA-T021 UI audit gate round-16: set when this screen was opened
  // while resolving a coordinator decision ("Zmień zapisaną regułę").
  respondsToDecisionRequiredId?: string | null;
  // Lets ControlPanel's Obsada tab (position dropdown) refresh its own
  // site-roles list right after a catalog change here, without a second
  // fetch owner or prop-drilled state.
  onRolesChanged?: () => void;
}) {
  const [rows, setRows] = useState<DraftRow[]>([]);
  const [regime, setRegime] = useState<"OCHRONA" | "ORDINARY">("OCHRONA");
  const [roles, setRoles] = useState<SiteRoleOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([api.getShiftCatalog(siteId), api.listSiteRoles(siteId)])
      .then(([res, siteRoles]) => {
        setRegime(res.planning_regime);
        setRows(res.shifts.length > 0 ? fromServer(res.shifts) : [blankRow()]);
        setRoles(siteRoles);
      })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [siteId]);

  const activeRoles = roles.filter((r) => r.active);

  const rolesChanged = () => {
    load();
    onRolesChanged?.();
  };

  const updateRow = (key: string, patch: Partial<DraftRow>) => {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));
    setSaved(false);
  };

  const toggleWeekday = (key: string, day: number) => {
    setRows((prev) =>
      prev.map((r) => {
        if (r.key !== key) return r;
        const active = r.active_weekdays.includes(day);
        // brief.md section 3, point 2: at least one weekday must stay
        // checked -- the last active day cannot be unchecked from the UI.
        if (active && r.active_weekdays.length === 1) return r;
        const next = active ? r.active_weekdays.filter((d) => d !== day) : [...r.active_weekdays, day].sort((a, b) => a - b);
        return { ...r, active_weekdays: next };
      }),
    );
    setSaved(false);
  };

  const addRow = () => {
    setRows((prev) => [...prev, blankRow()]);
    setSaved(false);
  };

  const removeRow = (key: string) => {
    if (rows.length <= 1) return;
    if (!window.confirm("Usunąć tę zmianę z katalogu?")) return;
    setRows((prev) => prev.filter((r) => r.key !== key));
    setSaved(false);
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      // ROTA-T065-CONFIGURABLE-ROLES section 5: every ORDINARY row must
      // have a role -- "— brak —" is gone (OWNER_DECISION 2026-09-13).
      // Checked here so the coordinator gets an immediate, specific
      // message instead of a generic server rejection.
      if (regime === "ORDINARY" && rows.some((r) => !r.required_role_id)) {
        throw new Error("Każda zmiana musi mieć przypisaną rolę.");
      }
      await api.putShiftCatalog(
        siteId,
        rows.map((r) => ({
          // ROTA-T065 audit R2-03 fix: OCHRONA never sends required_role_id
          // (the field is hidden and would be rejected by the backend);
          // ORDINARY never sends kind (irrelevant, backend defaults it).
          kind: regime === "OCHRONA" ? r.kind : null,
          start_time: r.start_time,
          end_time: r.end_time,
          required_primary_count: r.required_primary_count,
          active_weekdays: r.active_weekdays,
          required_role_id: regime === "ORDINARY" ? r.required_role_id : null,
        })),
        respondsToDecisionRequiredId,
      );
      setSaved(true);
    } catch (e: unknown) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p>Ładowanie…</p>;

  return (
    <>
      {regime === "ORDINARY" && <RoleCatalogPanel siteId={siteId} roles={roles} onChanged={rolesChanged} />}

      <div className="panel">
        <div className="panel-title-row">
          <div>
            <h3>Katalog zmian</h3>
            <p className="panel-hint">
              Każdy wiersz to jedna zmiana standardowa — rodzaj, godziny, ile osób, które dni tygodnia.
            </p>
          </div>
          <button className="btn-primary" data-diag-action="shift-catalog-add-row" onClick={addRow}>
            + Dodaj zmianę
          </button>
        </div>

        {error && <div className="banner-error">{error}</div>}

        {rows.map((row) => {
          const hours = durationHours(row.start_time, row.end_time);
          return (
            <div key={row.key} className="create-panel" style={{ marginBottom: 14 }}>
              <div className="create-panel-fields" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
                {/* ROTA-T065-CONFIGURABLE-ROLES section 5/9: "Rodzaj" (D/N)
                    is an OCHRONA-only concept. "Wymagana rola" is the
                    mirror-image ORDINARY-only field, mandatory (no
                    "— brak —") and drawn from this Site's own catalog. */}
                {regime === "OCHRONA" ? (
                  <label>
                    <span className="field-label">Rodzaj</span>
                    <select value={row.kind} onChange={(e) => updateRow(row.key, { kind: e.target.value as "D" | "N" })}>
                      <option value="D">Dniówka</option>
                      <option value="N">Nocka</option>
                    </select>
                  </label>
                ) : (
                  <label>
                    <span className="field-label">Wymagana rola</span>
                    <select
                      value={row.required_role_id}
                      onChange={(e) => updateRow(row.key, { required_role_id: e.target.value })}
                    >
                      <option value="" disabled>
                        — wybierz —
                      </option>
                      {activeRoles.map((r) => (
                        <option key={r.role_id} value={r.role_id}>
                          {r.display_name}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <label>
                  <span className="field-label">Początek</span>
                  <select value={row.start_time} onChange={(e) => updateRow(row.key, { start_time: e.target.value })}>
                    {HOUR_OPTIONS.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className="field-label">Koniec</span>
                  <select value={row.end_time} onChange={(e) => updateRow(row.key, { end_time: e.target.value })}>
                    {HOUR_OPTIONS.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className="field-label">Potrzebnych osób</span>
                  <input
                    type="number"
                    min={1}
                    value={row.required_primary_count}
                    onChange={(e) => updateRow(row.key, { required_primary_count: Number(e.target.value) })}
                  />
                </label>
              </div>

              <div className="chip-row" style={{ marginTop: 10, marginBottom: 10, flexWrap: "wrap" }}>
                {WEEKDAY_NAMES.map((name, i) => {
                  const day = i + 1;
                  const active = row.active_weekdays.includes(day);
                  const isLastActive = active && row.active_weekdays.length === 1;
                  return (
                    <button
                      key={day}
                      type="button"
                      className={`chip${active ? " chip-active" : ""}`}
                      data-diag-action="shift-catalog-toggle-weekday"
                      onClick={() => toggleWeekday(row.key, day)}
                      disabled={isLastActive}
                      title={isLastActive ? "Co najmniej jeden dzień musi pozostać zaznaczony" : undefined}
                    >
                      {name}
                    </button>
                  );
                })}
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, color: "var(--ink-faint)" }}>
                  {hours}h — {catalogKindLabel(hours)}
                </span>
                <button
                  className="btn-ghost"
                  data-diag-action="shift-catalog-remove-row"
                  onClick={() => removeRow(row.key)}
                  disabled={rows.length <= 1}
                  title={rows.length <= 1 ? "Ostatnią zmianę popraw przez edycję" : undefined}
                >
                  Usuń
                </button>
              </div>
            </div>
          );
        })}

        <div className="create-panel-actions">
          <button className="btn-primary" data-diag-action="shift-catalog-save" onClick={save} disabled={saving}>
            {saving ? "Zapisywanie…" : "Zapisz katalog"}
          </button>
          {saved && <span style={{ color: "var(--sage)", fontSize: 13, marginLeft: 12 }}>Zapisano.</span>}
        </div>
      </div>
    </>
  );
}
