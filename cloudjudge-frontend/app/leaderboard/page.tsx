"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getLeaderboard, type LeaderboardEntry } from "../../lib/api";

const DUMMY_ENTRIES: LeaderboardEntry[] = [
  { user_id: -1, username: "ByteSamurai", solved_problems: 42, total_submissions: 71, accepted_submissions: 53, success_rate: 74.6 },
  { user_id: -2, username: "AlgoNova", solved_problems: 37, total_submissions: 58, accepted_submissions: 41, success_rate: 70.7 },
  { user_id: -3, username: "StackSage", solved_problems: 33, total_submissions: 66, accepted_submissions: 39, success_rate: 59.1 },
  { user_id: -4, username: "GraphKnight", solved_problems: 31, total_submissions: 47, accepted_submissions: 35, success_rate: 74.4 },
  { user_id: -5, username: "DPQueen", solved_problems: 29, total_submissions: 52, accepted_submissions: 33, success_rate: 63.5 },
  { user_id: -6, username: "CachePilot", solved_problems: 27, total_submissions: 41, accepted_submissions: 30, success_rate: 73.2 },
  { user_id: -7, username: "QueueRunner", solved_problems: 25, total_submissions: 39, accepted_submissions: 27, success_rate: 69.2 },
  { user_id: -8, username: "TreeWalker", solved_problems: 23, total_submissions: 48, accepted_submissions: 28, success_rate: 58.3 },
  { user_id: -9, username: "LatencyHunter", solved_problems: 21, total_submissions: 37, accepted_submissions: 24, success_rate: 64.9 },
  { user_id: -10, username: "ScaleCraft", solved_problems: 19, total_submissions: 33, accepted_submissions: 21, success_rate: 63.6 },
  { user_id: -11, username: "HeapHero", solved_problems: 18, total_submissions: 31, accepted_submissions: 20, success_rate: 64.5 },
  { user_id: -12, username: "DesignSensei", solved_problems: 16, total_submissions: 27, accepted_submissions: 18, success_rate: 66.7 },
];

export default function LeaderboardPage() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const data = await getLeaderboard();
        setEntries(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load leaderboard");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const mergedEntries = useMemo(() => {
    const existing = new Set(entries.map((entry) => entry.username.toLowerCase()));
    const merged = [...entries, ...DUMMY_ENTRIES.filter((d) => !existing.has(d.username.toLowerCase()))];
    merged.sort(
      (a, b) =>
        b.solved_problems - a.solved_problems ||
        b.success_rate - a.success_rate ||
        b.accepted_submissions - a.accepted_submissions,
    );
    return merged;
  }, [entries]);

  return (
    <main className="page-shell panel">
      <div className="hero">
        <div>
          <h1>Global Leaderboard</h1>
          <p>Includes live user ranks plus seeded showcase profiles.</p>
        </div>
        <Link href="/" className="btn secondary">Dashboard</Link>
      </div>
      {loading ? <p>Loading leaderboard...</p> : null}
      {error ? <p className="error">{error}</p> : null}
      {!loading && !error ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>User</th>
                <th>Solved</th>
                <th>Accepted</th>
                <th>Submissions</th>
                <th>Success Rate</th>
              </tr>
            </thead>
            <tbody>
              {mergedEntries.map((entry, index) => {
                const isDummy = entry.user_id < 0;
                return (
                  <tr key={`${entry.user_id}-${entry.username}`}>
                    <td>#{index + 1}</td>
                    <td>
                      {entry.username} {isDummy ? <span className="chip">Showcase</span> : null}
                    </td>
                    <td>{entry.solved_problems}</td>
                    <td>{entry.accepted_submissions}</td>
                    <td>{entry.total_submissions}</td>
                    <td>{entry.success_rate.toFixed(1)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </main>
  );
}
