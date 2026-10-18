import { useState, useEffect } from "react";
import { api } from "../api.js";

export default function Admin() {
  const [users, setUsers] = useState(null);
  const [usage, setUsage] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    Promise.all([api.adminListUsers(), api.adminUsage()])
      .then(([u, s]) => { setUsers(u); setUsage(s); })
      .catch((e) => setError(e.message));
  }

  useEffect(load, []);

  async function toggle(user) {
    setBusy(true);
    setError("");
    try {
      await (user.is_active ? api.adminDisableUser(user.id) : api.adminEnableUser(user.id));
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (error) return <div className="panel"><div className="error">{error}</div></div>;
  if (!users || !usage) return <div className="panel"><div className="empty">Loading…</div></div>;

  return (
    <div>
      <div className="panel">
        <h2>Generation usage</h2>
        <div className="stat-grid">
          <div className="stat"><div className="num">{usage.total_requests}</div><div className="label">Total requests</div></div>
          <div className="stat"><div className="num" style={{ color: "var(--good)" }}>{usage.successful}</div><div className="label">Successful</div></div>
          <div className="stat"><div className="num" style={{ color: "var(--bad)" }}>{usage.failed}</div><div className="label">Failed</div></div>
        </div>
        {Object.keys(usage.by_kind).length > 0 && (
          <div className="chips">
            {Object.entries(usage.by_kind).map(([k, v]) => <span className="chip" key={k}>{k}: {v}</span>)}
          </div>
        )}
      </div>

      <div className="panel">
        <h2>Users</h2>
        <table className="admin-table">
          <thead><tr><th>Email</th><th>Role</th><th>Projects</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td>{u.role}</td>
                <td>{u.project_count}</td>
                <td><span className={`badge ${u.is_active ? "badge-active" : "badge-disabled"}`}>{u.is_active ? "active" : "disabled"}</span></td>
                <td>
                  {u.role !== "admin" && (
                    <button className="link" disabled={busy} onClick={() => toggle(u)}>
                      {u.is_active ? "Disable" : "Enable"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
