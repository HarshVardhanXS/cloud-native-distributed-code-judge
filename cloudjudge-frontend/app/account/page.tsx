"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  clearAuthToken,
  deleteMyAccount,
  getCurrentUser,
  type User,
} from "../../lib/api";

export default function AccountPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const me = await getCurrentUser();
        setUser(me);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unauthorized");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const logout = () => {
    clearAuthToken();
    window.location.href = "/login";
  };

  const handleDeleteAccount = async () => {
    const ok = window.confirm("Delete account permanently? This cannot be undone.");
    if (!ok) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await deleteMyAccount();
      clearAuthToken();
      setMessage(res.message);
      setTimeout(() => {
        window.location.href = "/register";
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete account");
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <main className="page-shell panel">Loading account...</main>;
  }

  return (
    <main className="page-shell panel">
      <div className="hero">
        <div>
          <h1>Account</h1>
          <p>Manage your profile and sign-in session.</p>
        </div>
        <Link href="/" className="btn secondary">Dashboard</Link>
      </div>
      {user ? (
        <>
          <p><strong>Username:</strong> {user.username}</p>
          <p><strong>Email:</strong> {user.email}</p>
          <p><strong>Created:</strong> {new Date(user.created_at).toLocaleString()}</p>
        </>
      ) : null}
      <div className="btn-row">
        <button className="btn secondary" onClick={logout}>Logout</button>
        <button className="btn danger" onClick={handleDeleteAccount} disabled={busy}>
          {busy ? "Deleting..." : "Delete account"}
        </button>
      </div>
      {message ? <p className="ok">{message}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </main>
  );
}
