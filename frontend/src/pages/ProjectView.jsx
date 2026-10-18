import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";

const PRIORITIES = ["High", "Medium", "Low"];
const LEVELS = ["High", "Medium", "Low"];

/** One requirement row: read mode, edit mode, and its review flag (REQ-AIGEN-03, REQ-REVIEW-01/02/03/05). */
function RequirementRow({ req, busy, onSave, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(req.text);

  useEffect(() => setText(req.text), [req.text]);

  async function save() {
    if (text.trim() !== req.text) await onSave(req.id, { text: text.trim() });
    setEditing(false);
  }

  return (
    <div className={`req-block ${req.flag_type ? "flagged" : ""}`}>
      <div className="req-row">
        <span className="req-id">{req.req_id}</span>
        {editing ? (
          <textarea className="req-edit" value={text} onChange={(e) => setText(e.target.value)} autoFocus />
        ) : (
          <span>{req.text}</span>
        )}
        <select
          className={`pri pri-${req.priority}`}
          value={req.priority}
          disabled={busy}
          onChange={(e) => onSave(req.id, { priority: e.target.value })}
          aria-label={`Priority of ${req.req_id}`}
        >
          {PRIORITIES.map((p) => <option key={p}>{p}</option>)}
        </select>
      </div>

      <div className="req-actions">
        {editing ? (
          <>
            <button className="link" onClick={save} disabled={busy || text.trim().length < 5}>Save</button>
            <button className="link" onClick={() => { setText(req.text); setEditing(false); }}>Cancel</button>
          </>
        ) : (
          <>
            <button className="link" onClick={() => setEditing(true)} disabled={busy}>Edit</button>
            <button className="link danger" onClick={() => onDelete(req.id)} disabled={busy}>Delete</button>
          </>
        )}
      </div>

      {req.flag_type && !editing && (
        <div className="flag">
          <div>
            <span className={`flag-tag flag-${req.flag_type}`}>{req.flag_type}</span> {req.flag_reason}
          </div>
          {req.suggestion && (
            <div className="suggestion">
              <span className="hint">{req.suggestion_kind === "rewrite" ? "Suggested rewording:" : "Suggestion:"}</span>{" "}
              {req.suggestion}
              {/* Only a drop-in rewrite can be applied; "advice" is an instruction, not requirement text. */}
              {req.suggestion_kind === "rewrite" && (
                <button className="link" onClick={() => onSave(req.id, { text: req.suggestion })} disabled={busy}>
                  Apply
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AddRequirement({ busy, onAdd }) {
  const [text, setText] = useState("");
  const [priority, setPriority] = useState("Medium");
  const [open, setOpen] = useState(false);

  if (!open) return <button className="ghost" onClick={() => setOpen(true)}>+ Add requirement</button>;

  async function submit(e) {
    e.preventDefault();
    await onAdd(text.trim(), priority);
    setText("");
    setOpen(false);
  }

  return (
    <form onSubmit={submit} className="add-req">
      <textarea placeholder="The system shall…" value={text} onChange={(e) => setText(e.target.value)} autoFocus />
      <div className="row">
        <select value={priority} onChange={(e) => setPriority(e.target.value)} aria-label="Priority">
          {PRIORITIES.map((p) => <option key={p}>{p}</option>)}
        </select>
        <button className="primary" type="submit" disabled={busy || text.trim().length < 5}>Add</button>
        <button className="ghost" type="button" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  );
}

export default function ProjectView() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.getProject(id).then(setProject).catch((e) => setError(e.message));
  }, [id]);

  /** Runs an API call that returns the updated project; one place for busy + error handling. */
  async function apply(call) {
    setBusy(true);
    setError("");
    try {
      setProject(await call());
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  /** Export doesn't update project state (it triggers a browser download), so it
   * can't reuse apply() as-is — same busy/error handling, different success path. */
  async function handleExport(format) {
    setBusy(true);
    setError("");
    try {
      await api.exportProject(id, format);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!project) {
    return <div className="panel">{error ? <div className="error">{error}</div> : <div className="empty">Loading…</div>}</div>;
  }

  const flaggedCount = project.requirements.filter((r) => r.flag_type).length;
  const reviewed = project.quality_score !== null;

  return (
    <div>
      {error && <div className="panel"><div className="error">{error}</div></div>}

      <div className="panel">
        <h2>Idea</h2>
        <p style={{ fontSize: 14.5, lineHeight: 1.6 }}>{project.idea_text}</p>
        <div className="chips" style={{ marginBottom: 12 }}>
          {project.classification_type && <span className="chip">{project.classification_type}</span>}
          {project.classification_domain && <span className="chip">{project.classification_domain}</span>}
          {project.classification_users && <span className="chip">{project.classification_users}</span>}
        </div>
        <div className="row" style={{ marginTop: 0 }}>
          <span className="status-chip">{project.status}</span>
          {project.status === "Draft" && (
            <button className="ghost" onClick={() => apply(() => api.markReviewed(id))} disabled={busy}>
              Mark as Reviewed
            </button>
          )}
          <button className="ghost" disabled={busy} onClick={() => handleExport("pdf")}>Download PDF</button>
          <button className="ghost" disabled={busy} onClick={() => handleExport("docx")}>Download Word</button>
        </div>
      </div>

      <div className="panel">
        <h2>Quality review</h2>
        {!reviewed ? (
          <p className="hint" style={{ marginTop: 0 }}>
            {project.requirements.length === 0
              ? "Add a requirement to enable review."
              : "Checks for vague wording, near-duplicate requirements and missing coverage. Re-run after editing."}
          </p>
        ) : (
          <div className="score-row">
            <div className={`score ${project.quality_score >= 80 ? "good" : project.quality_score >= 50 ? "mid" : "low"}`}>
              {project.quality_score}
              <span>/100</span>
            </div>
            <div className="hint">
              {flaggedCount} of {project.requirements.length} requirements flagged
              {project.missing_areas.length > 0 && ` · ${project.missing_areas.length} coverage gaps`}
            </div>
          </div>
        )}
        <div className="row">
          <button
            className="primary"
            onClick={() => apply(() => api.runQualityReview(id))}
            disabled={busy || project.requirements.length === 0}
          >
            {busy ? "Working…" : reviewed ? "Re-run review" : "Run quality review"}
          </button>
        </div>

        {reviewed && project.missing_areas.length > 0 && (
          <div style={{ marginTop: 18 }}>
            <div className="hint" style={{ marginBottom: 8 }}>Commonly expected areas with no matching requirement:</div>
            <div className="chips">
              {project.missing_areas.map((a) => <span className="chip chip-warn" key={a}>{a}</span>)}
            </div>
          </div>
        )}
      </div>

      <div className="panel">
        <h2>Functional requirements</h2>
        {project.requirements.length === 0 && <div className="empty">No requirements yet.</div>}
        {project.requirements.map((r) => (
          <RequirementRow
            key={r.id}
            req={r}
            busy={busy}
            onSave={(reqPk, patch) => apply(() => api.updateRequirement(id, reqPk, patch))}
            onDelete={(reqPk) => apply(() => api.deleteRequirement(id, reqPk))}
          />
        ))}
        <div style={{ marginTop: 14 }}>
          <AddRequirement busy={busy} onAdd={(text, priority) => apply(() => api.addRequirement(id, text, priority))} />
        </div>
      </div>

      <div className="panel">
        <h2>User stories</h2>
        {project.user_stories.length === 0 && <div className="empty">None generated.</div>}
        {project.user_stories.map((s, i) => (
          <div className="story-card" key={i}>
            As a <b>{s.role}</b>, I want {s.goal}, so that {s.benefit}.
          </div>
        ))}
      </div>

      <div className="panel">
        <h2>Use cases</h2>
        {project.use_cases.length === 0 && <div className="empty">None generated.</div>}
        {project.use_cases.map((u, i) => (
          <div className="usecase" key={i}>
            <div className="usecase-title">{u.name} <span className="chip">{u.actor}</span></div>
            <dl>
              {u.precondition && (<><dt>Precondition</dt><dd>{u.precondition}</dd></>)}
              <dt>Main flow</dt><dd>{u.main_flow}</dd>
              {u.postcondition && (<><dt>Postcondition</dt><dd>{u.postcondition}</dd></>)}
            </dl>
          </div>
        ))}
      </div>

      <div className="panel">
        <h2>Risks</h2>
        {project.risks.length === 0 && <div className="empty">None generated.</div>}
        {project.risks.map((r) => (
          <div className="risk-row" key={r.id}>
            <div className="risk-desc">{r.description}</div>
            <div className="risk-controls">
              <select value={r.likelihood} disabled={busy}
                onChange={(e) => apply(() => api.updateRisk(id, r.id, { likelihood: e.target.value }))}>
                {LEVELS.map((l) => <option key={l}>{l}</option>)}
              </select>
              <select value={r.impact} disabled={busy}
                onChange={(e) => apply(() => api.updateRisk(id, r.id, { impact: e.target.value }))}>
                {LEVELS.map((l) => <option key={l}>{l}</option>)}
              </select>
              <button className="link danger" onClick={() => apply(() => api.deleteRisk(id, r.id))} disabled={busy}>Delete</button>
            </div>
            <div className="risk-mitigation hint">
              {r.mitigation ? <>Mitigation: {r.mitigation}</> : "No mitigation noted."}
            </div>
          </div>
        ))}
      </div>

      <div className="panel">
        <h2>Cost estimate</h2>
        {project.cost_estimates.length === 0 ? <div className="empty">None generated.</div> : (
          <table>
            <thead><tr><th>Area</th><th>Effort</th><th>Notes</th></tr></thead>
            <tbody>
              {project.cost_estimates.map((c) => (
                <tr key={c.id}>
                  <td>{c.area}</td>
                  <td>
                    <select value={c.effort_level} disabled={busy}
                      onChange={(e) => apply(() => api.updateCostEstimate(id, c.id, { effort_level: e.target.value }))}>
                      {LEVELS.map((l) => <option key={l}>{l}</option>)}
                    </select>
                  </td>
                  <td className="hint">{c.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <SprintPlanner project={project} id={id} busy={busy} apply={apply} />

      <div className="panel">
        <h2>Test cases</h2>
        {project.test_cases.length === 0 ? <div className="empty">None generated.</div> : (
          <table>
            <thead><tr><th>Feature</th><th>Input</th><th>Expected result</th></tr></thead>
            <tbody>
              {project.test_cases.map((t, i) => (
                <tr key={i}><td>{t.feature}</td><td>{t.input_condition}</td><td>{t.expected_result}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function SprintPlanner({ project, id, busy, apply }) {
  const [sprintCount, setSprintCount] = useState(5);
  const [duration, setDuration] = useState(1);
  const hasPlan = project.sprints.length > 0;

  async function handleGenerate(e) {
    e.preventDefault();
    await apply(() => api.generateSprintPlan(id, Number(sprintCount), Number(duration)));
  }

  return (
    <div className="panel">
      <h2>Sprint plan</h2>
      {!hasPlan && <p className="hint" style={{ marginTop: 0 }}>Generate a sprint plan to distribute user stories by priority (REQ-SPRINT-01/02).</p>}

      <form onSubmit={handleGenerate} className="row" style={{ marginTop: 0 }}>
        <label style={{ margin: 0 }}>
          Sprints
          <input type="number" min={1} max={12} value={sprintCount}
            onChange={(e) => setSprintCount(e.target.value)} style={{ width: 64, marginLeft: 6 }} />
        </label>
        <label style={{ margin: 0 }}>
          Weeks each
          <input type="number" min={0.5} max={6} step={0.5} value={duration}
            onChange={(e) => setDuration(e.target.value)} style={{ width: 64, marginLeft: 6 }} />
        </label>
        <button className="primary" type="submit" disabled={busy || project.user_stories.length === 0}>
          {hasPlan ? "Regenerate plan" : "Generate plan"}
        </button>
      </form>

      {hasPlan && (
        <div className="sprint-grid">
          {project.sprints.map((s) => (
            <div className="sprint-col" key={s.id}>
              <div className="sprint-col-head">Sprint {s.sprint_no} <span className="hint">· {s.duration_weeks}w</span></div>
              {s.stories.length === 0 && <div className="empty" style={{ padding: "8px 0" }}>Empty</div>}
              {s.stories.map((story) => (
                <div className="sprint-story" key={story.id}>
                  <div>As a {story.role}, I want {story.goal}.</div>
                  <select
                    value={s.sprint_no}
                    disabled={busy}
                    onChange={(e) => apply(() => api.moveStory(id, story.id, Number(e.target.value)))}
                  >
                    {project.sprints.map((opt) => <option key={opt.sprint_no} value={opt.sprint_no}>Move to sprint {opt.sprint_no}</option>)}
                  </select>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

