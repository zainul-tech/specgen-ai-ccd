import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

export default function Dashboard() {
  const [idea, setIdea] = useState("");
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .listProjects()
      .then(setProjects)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingList(false));
  }, []);

  async function handleGenerate(e) {
    e.preventDefault();
    setError("");
    if (idea.trim().length < 15) {
      setError("Describe your idea in at least a full sentence.");
      return;
    }
    setBusy(true);
    try {
      // REQ-SUBMIT-01/02 + REQ-AIGEN-01: submit and generate in one call for this increment.
      const project = await api.createProject(idea.trim());
      navigate(`/projects/${project.id}`);
    } catch (err) {
      // REQ-SUBMIT-04: surfaced clearly, including "no API key configured" during dev.
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <h2>New project idea</h2>
      <form onSubmit={handleGenerate}>
        <textarea
          placeholder="e.g. Develop an online food ordering app for restaurants with live tracking and payment."
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
        />
        <div className="row">
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Generating…" : "Generate draft →"}
          </button>
          <span className="hint">This calls the AI Processing Engine and may take a few seconds.</span>
        </div>
        {error && <div className="error">{error}</div>}
      </form>

      <h2 style={{ marginTop: 28 }}>Your projects</h2>
      {loadingList && <div className="empty">Loading…</div>}
      {!loadingList && projects.length === 0 && <div className="empty">No projects yet — submit an idea above.</div>}
      {projects.map((p) => (
        <a key={p.id} className="project-list-item" href={`/projects/${p.id}`} onClick={(e) => { e.preventDefault(); navigate(`/projects/${p.id}`); }}>
          <span className="idea-text">{p.idea_text.length > 70 ? p.idea_text.slice(0, 70) + "…" : p.idea_text}</span>
          <span className="status-chip">{p.status}</span>
        </a>
      ))}
    </div>
  );
}
