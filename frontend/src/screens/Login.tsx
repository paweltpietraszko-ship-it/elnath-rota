// ROTA-T024-TESTER-LOGIN-ISOLATION (brief.md section 10): a simple
// login screen for a CENTRAL_SERVICE deployment -- no self-registration,
// no "forgot password" link (brief section 4: operator resets manually).
// Never stores the password/token in localStorage/sessionStorage; the
// session lives entirely in the HttpOnly cookie the backend sets.
import { useState } from "react";
import { authApi } from "../api/client";

export default function Login({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await authApi.login(email, password);
      onLoggedIn();
    } catch (err: unknown) {
      setError(String((err as Error).message ?? err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ width: "100vw", height: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <form
        onSubmit={handleSubmit}
        style={{
          background: "var(--surface, #fff)", border: "1px solid var(--ink-faint, #ddd)",
          borderRadius: 12, padding: "40px 48px", width: 360,
        }}
      >
        <h1 className="brand-font" style={{ fontSize: 20, fontWeight: 600, marginBottom: 4, textAlign: "center" }}>
          Elnath Rota
        </h1>
        <p style={{ color: "var(--ink-soft)", fontSize: 13.5, marginBottom: 24, textAlign: "center" }}>
          Zaloguj się, aby kontynuować.
        </p>

        <div className="create-panel-fields">
          <label>
            <span className="field-label">E-mail</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
              required
              style={{ width: "100%", marginBottom: 16, boxSizing: "border-box" }}
            />
          </label>

          <label>
            <span className="field-label">Hasło</span>
            <div style={{ position: "relative", marginBottom: 16 }}>
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{ width: "100%", boxSizing: "border-box", paddingRight: 40 }}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                tabIndex={-1}
                className="btn-ghost"
                style={{ position: "absolute", right: 4, top: 2, padding: "4px 8px" }}
              >
                {showPassword ? "Ukryj" : "Pokaż"}
              </button>
            </div>
          </label>
        </div>

        {error && (
          <div className="banner-error" style={{ marginBottom: 16 }}>
            {error}
          </div>
        )}

        <button type="submit" className="btn-primary" disabled={loading} style={{ width: "100%" }}>
          {loading ? "Logowanie…" : "Zaloguj się"}
        </button>
      </form>
    </div>
  );
}
