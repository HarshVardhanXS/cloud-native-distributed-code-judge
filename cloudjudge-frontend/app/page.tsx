"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  clearAuthToken,
  getCurrentUser,
  getLeaderboard,
  getStats,
  listProblems,
  login,
  register,
  setAuthToken,
  type LeaderboardEntry,
  type Problem,
  type User,
} from "../lib/api";

type Stats = {
  total_submissions: number;
  passed_submissions: number;
  unique_problems_solved: number;
  success_rate: number;
};

type AuthMode = "login" | "register";

export default function HomePage() {
  const [user, setUser] = useState<User | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState("");

  const topProblems = useMemo(() => problems.slice(0, 6), [problems]);
  const topLeaderboard = useMemo(() => leaderboard.slice(0, 8), [leaderboard]);

  const refreshSession = async () => {
    try {
      const me = await getCurrentUser();
      setUser(me);
      const myStats = await getStats();
      setStats(myStats);
    } catch {
      setUser(null);
      setStats(null);
    }
  };

  useEffect(() => {
    async function bootstrap() {
      setLoading(true);
      await Promise.all([
        refreshSession(),
        listProblems().then(setProblems).catch(() => setProblems([])),
        getLeaderboard().then(setLeaderboard).catch(() => setLeaderboard([])),
      ]);
      setLoading(false);
    }
    bootstrap();
  }, []);

  useEffect(() => {
    if (!loading && !user) {
      const t = window.setTimeout(() => setAuthOpen(true), 350);
      return () => window.clearTimeout(t);
    }
  }, [loading, user]);

  const handleLogout = () => {
    clearAuthToken();
    setUser(null);
    setStats(null);
    setAuthOpen(true);
  };

  const handleAuthSubmit = async () => {
    setAuthError("");
    setAuthBusy(true);
    try {
      if (authMode === "register") {
        await register({ username, email, password });
      }
      const token = await login(username, password);
      setAuthToken(token.access_token);
      await refreshSession();
      setAuthOpen(false);
      setPassword("");
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setAuthBusy(false);
    }
  };

  return (
    <main className="page-shell">
      <section className="hero-banner fade-in-up">
        <h1 style={{ marginTop: 0, marginBottom: 6 }}>Cloud Judge Dashboard</h1>
        <p style={{ margin: 0 }}>
          Solve coding and system design challenges, track progress, and compare on leaderboard.
        </p>
      </section>

      <section className="panel fade-in-up" style={{ marginTop: "1rem" }}>
        <div className="hero">
          <div>
            <h2 className="section-title" style={{ marginBottom: 4 }}>
              {user ? `Welcome back, ${user.username}` : "Explore as guest"}
            </h2>
            <p style={{ margin: 0, color: "var(--muted)" }}>
              {user
                ? `Success rate ${((stats?.success_rate ?? 0)).toFixed(1)}% across ${stats?.total_submissions ?? 0} submissions.`
                : "You can browse all problems and leaderboard now. Sign in to submit and track full history."}
            </p>
          </div>
          <div className="btn-row">
            <Link href="/problems" className="btn">Problems</Link>
            <Link href="/leaderboard" className="btn secondary">Leaderboard</Link>
            {user ? (
              <>
                <Link href="/create-problem" className="btn secondary">Publish</Link>
                <Link href="/account" className="btn secondary">Account</Link>
                <button className="btn danger" onClick={handleLogout}>Logout</button>
              </>
            ) : (
              <button className="btn secondary" onClick={() => setAuthOpen(true)}>Sign In / Sign Up</button>
            )}
          </div>
        </div>

        <div className="grid-stats">
          <div className="stat-card">
            <p className="stat-label">Total Problems</p>
            <p className="stat-value">{problems.length}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Leaderboard Users</p>
            <p className="stat-value">{leaderboard.length}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Solved (You)</p>
            <p className="stat-value">{stats?.unique_problems_solved ?? 0}</p>
          </div>
          <div className="stat-card">
            <p className="stat-label">Accepted (You)</p>
            <p className="stat-value">{stats?.passed_submissions ?? 0}</p>
          </div>
        </div>
      </section>

      <section className="panel" style={{ marginTop: "1rem" }}>
        <h2 className="section-title">Problem Spotlight</h2>
        {loading ? <p>Loading problems...</p> : null}
        {!loading ? (
          <div className="problem-grid stagger">
            {topProblems.map((problem) => (
              <article key={problem.id} className="problem-card">
                <p style={{ marginTop: 0, marginBottom: 6 }}>
                  <strong>{problem.title}</strong>
                </p>
                <p style={{ marginTop: 0, color: "var(--muted)", minHeight: 40 }}>
                  {problem.description.slice(0, 96)}
                  {problem.description.length > 96 ? "..." : ""}
                </p>
                <div className="btn-row">
                  <span className="chip">{problem.difficulty}</span>
                  <Link className="btn secondary" href={`/problems/${problem.id}`}>Open</Link>
                </div>
              </article>
            ))}
          </div>
        ) : null}
      </section>

      <section className="panel" style={{ marginTop: "1rem" }}>
        <h2 className="section-title">Leaderboard Preview</h2>
        {loading ? <p>Loading leaderboard...</p> : null}
        {!loading ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>User</th>
                  <th>Solved</th>
                  <th>Success</th>
                </tr>
              </thead>
              <tbody>
                {topLeaderboard.map((entry, index) => (
                  <tr key={`${entry.user_id}-${entry.username}`}>
                    <td>#{index + 1}</td>
                    <td>{entry.username}</td>
                    <td>{entry.solved_problems}</td>
                    <td>{entry.success_rate.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {authOpen ? (
        <div className="modal-backdrop" onClick={() => setAuthOpen(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="hero" style={{ marginBottom: 8 }}>
              <h3 style={{ margin: 0 }}>Get Started</h3>
              <button className="btn secondary" onClick={() => setAuthOpen(false)}>Close</button>
            </div>
            <div className="modal-tabs">
              <button
                className={`tab-btn ${authMode === "login" ? "active" : ""}`}
                onClick={() => setAuthMode("login")}
              >
                Sign In
              </button>
              <button
                className={`tab-btn ${authMode === "register" ? "active" : ""}`}
                onClick={() => setAuthMode("register")}
              >
                Sign Up
              </button>
            </div>
            <div className="stack">
              <input className="field" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
              {authMode === "register" ? (
                <input className="field" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
              ) : null}
              <input className="field" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <button
                className="btn"
                onClick={handleAuthSubmit}
                disabled={authBusy || !username || !password || (authMode === "register" && !email)}
              >
                {authBusy ? "Please wait..." : authMode === "login" ? "Sign In" : "Create Account"}
              </button>
              {authError ? <p className="error">{authError}</p> : null}
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
