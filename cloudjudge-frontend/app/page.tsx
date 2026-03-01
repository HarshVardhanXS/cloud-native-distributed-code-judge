"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";

export default function HomePage() {
  const [user, setUser] = useState<{ username: string; email: string } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchUser() {
      try {
        const data = await apiFetch("/me");
        setUser(data);
      } catch {
        setError("Not authenticated");
      }
    }

    fetchUser();
  }, []);

  return (
    <div style={{ padding: 40 }}>
      <h1>Cloud Judge</h1>

      {user ? (
        <>
          <p>Logged in as: {user.username}</p>
          <p>Email: {user.email}</p>
        </>
      ) : (
        <p>{error}</p>
      )}
    </div>
  );
}
