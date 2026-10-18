import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api, setToken } from "../api.js";

export default function Register({ onAuth }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      // REQ-AUTH-01: mirrors backend's min_length=8 for immediate feedback.
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      await api.register(email, password);
      const { access_token } = await api.login(email, password);
      setToken(access_token);
      onAuth();
      navigate("/");
    } catch (err) {
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
        <h2>Create an account</h2>
        <form onSubmit={handleSubmit}>
          <label htmlFor="email">Email</label>
          <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <label htmlFor="password">Password</label>
          <input id="password" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
          <div className="row">
            <button className="primary" type="submit" disabled={busy}>
              {busy ? "Creating…" : "Create account"}
            </button>
            <span className="hint">
              Have an account? <Link to="/login" style={{ color: "var(--accent)" }}>Log in</Link>
            </span>
          </div>
          {error && <div className="error">{error}</div>}
        </form>
      </div>
    </div>
  );
}
