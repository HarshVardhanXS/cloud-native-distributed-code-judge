"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listProblems, type Problem } from "../../lib/api";

export default function ProblemsPage() {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadProblems() {
      try {
        const data = await listProblems();
        setProblems(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load problems");
      } finally {
        setLoading(false);
      }
    }

    loadProblems();
  }, []);

  return (
    <main className="page-shell panel">
      <div className="hero">
        <div>
          <h1>Problems</h1>
          <p>Choose a challenge and start solving.</p>
        </div>
        <div className="btn-row">
          <Link href="/" className="btn secondary">Dashboard</Link>
        </div>
      </div>
      {loading ? <p>Loading...</p> : null}
      {error ? <p className="error">{error}</p> : null}
      {!loading && !error ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Difficulty</th>
                <th>Tags</th>
                <th>Open</th>
              </tr>
            </thead>
            <tbody>
              {problems.map((problem) => (
                <tr key={problem.id}>
                  <td>{problem.title}</td>
                  <td>
                    <span className="chip">{problem.difficulty}</span>
                  </td>
                  <td>{problem.tags?.join(", ") || "-"}</td>
                  <td>
                    <Link href={`/problems/${problem.id}`} className="btn">Solve</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </main>
  );
}
