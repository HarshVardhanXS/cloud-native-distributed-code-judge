"use client";

import Link from "next/link";
import { useState } from "react";
import { login, register, setAuthToken } from "../../lib/api";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleRegister = async () => {
    setError("");
    setLoading(true);
    try {
      await register({ username, email, password });
      const token = await login(username, password);
      setAuthToken(token.access_token);
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page-shell panel" style={{ maxWidth: 460 }}>
      <h1 style={{ marginTop: 0 }}>Create Account</h1>
      <div className="stack">
        <input
          className="field"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          className="field"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="field"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button className="btn" onClick={handleRegister} disabled={loading || !username || !email || !password}>
          {loading ? "Creating account..." : "Register"}
        </button>
      </div>
      {error ? <p className="error" style={{ marginTop: 10 }}>{error}</p> : null}
      <p style={{ marginTop: 16, color: "var(--muted)" }}>
        Already have an account? <Link href="/login">Login</Link>
      </p>
    </main>
  );
}
