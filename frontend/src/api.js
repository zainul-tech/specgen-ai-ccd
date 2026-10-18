const BASE_URL = import.meta.env.VITE_API_URL !== undefined
  ? import.meta.env.VITE_API_URL
  : (typeof window !== "undefined" && window.location.port === "5173" ? "http://localhost:8000" : "");

function getToken() {
  return localStorage.getItem("specgen_token");
}

export function setToken(token) {
  if (token) localStorage.setItem("specgen_token", token);
  else localStorage.removeItem("specgen_token");
}

export function isLoggedIn() {
  return !!getToken();
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch (_) {}
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  register: (email, password) =>
    request("/auth/register", { method: "POST", body: { email, password }, auth: false }),
  login: (email, password) =>
    request("/auth/login", { method: "POST", body: { email, password }, auth: false }),
  me: () => request("/auth/me"),
  listProjects: () => request("/projects"),
  getProject: (id) => request(`/projects/${id}`),
  createProject: (idea_text) => request("/projects", { method: "POST", body: { idea_text } }),
  markReviewed: (id) => request(`/projects/${id}/review`, { method: "PATCH" }),
  runQualityReview: (id) => request(`/projects/${id}/quality-review`, { method: "POST" }),
  addRequirement: (id, text, priority) =>
    request(`/projects/${id}/requirements`, { method: "POST", body: { text, priority } }),
  updateRequirement: (id, reqPk, patch) =>
    request(`/projects/${id}/requirements/${reqPk}`, { method: "PATCH", body: patch }),
  deleteRequirement: (id, reqPk) =>
    request(`/projects/${id}/requirements/${reqPk}`, { method: "DELETE" }),
  updateRisk: (id, riskPk, patch) =>
    request(`/projects/${id}/risks/${riskPk}`, { method: "PATCH", body: patch }),
  deleteRisk: (id, riskPk) =>
    request(`/projects/${id}/risks/${riskPk}`, { method: "DELETE" }),
  updateCostEstimate: (id, costPk, patch) =>
    request(`/projects/${id}/cost-estimate/${costPk}`, { method: "PATCH", body: patch }),
  generateSprintPlan: (id, sprintCount, durationWeeks) =>
    request(`/projects/${id}/sprint-plan`, { method: "POST", body: { sprint_count: sprintCount, duration_weeks: durationWeeks } }),
  moveStory: (id, storyPk, sprintNo) =>
    request(`/projects/${id}/stories/${storyPk}/sprint`, { method: "PATCH", body: { sprint_no: sprintNo } }),

  // Export — not JSON, so it bypasses request() and handles the blob + download itself.
  exportProject: async (id, format) => {
    const token = getToken();
    const res = await fetch(`${BASE_URL}/projects/${id}/export?format=${format}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      let detail = `Export failed (${res.status})`;
      try { detail = (await res.json()).detail || detail; } catch (_) {}
      throw new Error(detail);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    const filename = match ? match[1] : `specgen-ai-project-${id}.${format}`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  // Admin
  adminListUsers: () => request("/admin/users"),
  adminUsage: () => request("/admin/usage"),
  adminDisableUser: (userId) => request(`/admin/users/${userId}/disable`, { method: "PATCH" }),
  adminEnableUser: (userId) => request(`/admin/users/${userId}/enable`, { method: "PATCH" }),
};
