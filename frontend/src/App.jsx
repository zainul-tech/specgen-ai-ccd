import { useState, useEffect } from "react";
import { Routes, Route, Navigate, Link, useNavigate } from "react-router-dom";
import { isLoggedIn, setToken, api } from "./api.js";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ProjectView from "./pages/ProjectView.jsx";
import Admin from "./pages/Admin.jsx";

function RequireAuth({ loggedIn, children }) {
  if (!loggedIn) return <Navigate to="/login" replace />;
  return children;
}

function RequireAdmin({ loggedIn, user, children }) {
  if (!loggedIn) return <Navigate to="/login" replace />;
  if (user === undefined) return null; // still loading the current user
  if (!user || user.role !== "admin") return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(isLoggedIn());
  const [user, setUser] = useState(undefined); // undefined = loading, null = unknown/error
  const navigate = useNavigate();

  useEffect(() => {
    if (!loggedIn) { setUser(null); return; }
    api.me().then(setUser).catch(() => setUser(null));
  }, [loggedIn]);

  function handleLogout() {
    setToken(null);
    setLoggedIn(false);
    setUser(null);
    navigate("/login");
  }

  return (
    <div>
      {loggedIn && (
        <div className="wrap" style={{ paddingBottom: 0 }}>
          <header className="app">
            <div className="mark">
              <Link to="/">SPEC<span>GEN</span> AI</Link>
            </div>
            <nav className="app">
              <Link to="/">New idea</Link>
              {user?.role === "admin" && <Link to="/admin">Admin</Link>}
              <button onClick={handleLogout}>Log out</button>
            </nav>
          </header>
        </div>
      )}
      <div className={loggedIn ? "wrap" : ""} style={loggedIn ? { paddingTop: 0 } : {}}>
        <Routes>
          <Route path="/login" element={loggedIn ? <Navigate to="/" replace /> : <Login onAuth={() => setLoggedIn(true)} />} />
          <Route path="/register" element={loggedIn ? <Navigate to="/" replace /> : <Register onAuth={() => setLoggedIn(true)} />} />
          <Route path="/" element={<RequireAuth loggedIn={loggedIn}><Dashboard /></RequireAuth>} />
          <Route path="/projects/:id" element={<RequireAuth loggedIn={loggedIn}><ProjectView /></RequireAuth>} />
          <Route path="/admin" element={<RequireAdmin loggedIn={loggedIn} user={user}><Admin /></RequireAdmin>} />
        </Routes>
      </div>
    </div>
  );
}
