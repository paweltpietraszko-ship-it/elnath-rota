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
    <div className="login-screen">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-brand">
          <div className="login-brand-mark">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M12 2v6M12 16v6M2 12h6M16 12h6" />
            </svg>
          </div>
          <div>
            <h1 className="brand-font login-title">Elnath Rota</h1>
            <p className="login-subtitle">Zaloguj się, aby kontynuować.</p>
          </div>
        </div>

        <div className="create-panel-fields" style={{ gridTemplateColumns: "1fr", marginBottom: 0 }}>
          <label>
            <span className="field-label">E-mail</span>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus required />
          </label>

          <label>
            <span className="field-label">Hasło</span>
            <div className="login-password-row">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                tabIndex={-1}
                className="btn-ghost login-password-toggle"
              >
                {showPassword ? "Ukryj" : "Pokaż"}
              </button>
            </div>
          </label>
        </div>

        {error && (
          <div className="banner-error" style={{ marginTop: 18 }}>
            {error}
          </div>
        )}

        <button type="submit" className="btn-primary login-submit" disabled={loading} style={{ marginTop: error ? 0 : 22 }}>
          {loading ? "Logowanie…" : "Zaloguj się"}
        </button>
      </form>
    </div>
  );
}
