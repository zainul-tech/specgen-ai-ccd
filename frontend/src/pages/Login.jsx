import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api, setToken } from "../api.js";

export default function Login({ onAuth }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      onAuth();
      navigate("/");
    } catch (err) {
      // REQ-AUTH-03: backend already returns a generic message; shown as-is.
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="wrap" style={{ maxWidth: 420 }}>
      <div className="mark" style={{ marginBottom: 24 }}>
        SPEC<span>GEN</span> AI
      </div>
      <div className="panel">
        <h2>Log in</h2>
        <form onSubmit={handleSubmit}>
          <label htmlFor="email">Email</label>
          <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <label htmlFor="password">Password</label>
          <input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          <div className="row">
            <button className="primary" type="submit" disabled={busy}>
              {busy ? "Logging in…" : "Log in"}
            </button>
            <span className="hint">
              No account? <Link to="/register" style={{ color: "var(--accent)" }}>Register</Link>
            </span>
          </div>
          {error && <div className="error">{error}</div>}
        </form>
      </div>
    </div>
  );
}
