"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  createProblemDiscussion,
  getProblem,
  getProblemDetails,
  getProblemTestcases,
  listMyProblemSubmissions,
  listProblemDiscussions,
  parseSubmissionResult,
  submitSolution,
  type Discussion,
  type Problem,
  type ProblemDetails,
  type Submission,
  type TestCase,
} from "../../../lib/api";

type TabKey =
  | "description"
  | "examples"
  | "constraints"
  | "answer"
  | "diagram"
  | "discussions"
  | "history"
  | "analytics";
type Language = "python" | "javascript" | "java" | "cpp";

type DiagramNode = {
  id: number;
  label: string;
  x: number;
  y: number;
};

const LANGUAGE_TEMPLATES: Record<Language, string> = {
  python: "def solution(a, b):\n    return a + b",
  javascript: "function solution(a, b) {\n  return a + b;\n}",
  java: "class Solution {\n  public int solution(int a, int b) {\n    return a + b;\n  }\n}",
  cpp: "#include <bits/stdc++.h>\nusing namespace std;\n\nint solution(int a, int b) {\n  return a + b;\n}",
};

const DUMMY_DISCUSSIONS: Array<Pick<Discussion, "id" | "username" | "content" | "created_at">> = [
  { id: -300, username: "ScaleWizard", content: "Start with assumptions and define p95 latency + availability target first.", created_at: new Date(Date.now() - 56 * 60 * 60 * 1000).toISOString() },
  { id: -301, username: "InfraNerd", content: "Use queue + worker isolation for long-running evaluation tasks.", created_at: new Date(Date.now() - 45 * 60 * 60 * 1000).toISOString() },
  { id: -302, username: "AlgoPilot", content: "For coding versions, keep an O(n) baseline plus edge-case walkthrough.", created_at: new Date(Date.now() - 30 * 60 * 60 * 1000).toISOString() },
  { id: -303, username: "DesignOps", content: "Cache leaderboard snapshots every 5 seconds in Redis sorted sets.", created_at: new Date(Date.now() - 21 * 60 * 60 * 1000).toISOString() },
  { id: -304, username: "ByteGuru", content: "State trade-offs explicitly: polling vs websocket, SQL vs NoSQL.", created_at: new Date(Date.now() - 16 * 60 * 60 * 1000).toISOString() },
  { id: -305, username: "ProdArchitect", content: "Include observability in your answer: traces, logs, alert rules.", created_at: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString() },
];

export default function ProblemDetailPage() {
  const params = useParams<{ id?: string }>();
  const idParam = Array.isArray(params.id) ? params.id[0] : params.id;
  const problemId = useMemo(() => Number(idParam), [idParam]);

  const [problem, setProblem] = useState<Problem | null>(null);
  const [details, setDetails] = useState<ProblemDetails | null>(null);
  const [testcases, setTestcases] = useState<TestCase[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [activeTab, setActiveTab] = useState<TabKey>("description");
  const [language, setLanguage] = useState<Language>("python");
  const [code, setCode] = useState(LANGUAGE_TEMPLATES.python);
  const [discussionDraft, setDiscussionDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [postingDiscussion, setPostingDiscussion] = useState(false);
  const [error, setError] = useState("");
  const [historyError, setHistoryError] = useState("");
  const [discussionError, setDiscussionError] = useState("");
  const [diagramTool, setDiagramTool] = useState("Service");
  const [diagramNodes, setDiagramNodes] = useState<DiagramNode[]>([
    { id: 1, label: "Client", x: 20, y: 30 },
    { id: 2, label: "API Gateway", x: 220, y: 30 },
    { id: 3, label: "Service", x: 420, y: 30 },
  ]);
  const [dragNodeId, setDragNodeId] = useState<number | null>(null);
  const dragOffset = useRef({ x: 0, y: 0 });

  const mergedDiscussions = useMemo(() => {
    const existing = new Set(discussions.map((discussion) => discussion.username.toLowerCase()));
    const dummy: Discussion[] = DUMMY_DISCUSSIONS
      .filter((discussion) => !existing.has(discussion.username.toLowerCase()))
      .map((discussion) => ({
        id: discussion.id,
        problem_id: problemId,
        user_id: -1,
        username: discussion.username,
        content: discussion.content,
        created_at: discussion.created_at,
      }));
    return [...discussions, ...dummy].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [discussions, problemId]);

  const analytics = useMemo(() => {
    const real = submissions
      .slice()
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      .slice(-24)
      .map((submission) => {
        const parsed = parseSubmissionResult(submission.result);
        const passed = parsed.passed_test_cases ?? (submission.status === "accepted" ? 1 : 0);
        const total = parsed.total_test_cases ?? 1;
        const pct = total > 0 ? Math.round((passed / total) * 100) : 0;
        return { id: submission.id, pct: Math.max(8, pct), label: `${passed}/${total}` };
      });
    if (real.length > 0) return real;

    return [
      { id: -1, pct: 18, label: "1/5" }, { id: -2, pct: 37, label: "2/5" }, { id: -3, pct: 55, label: "3/5" },
      { id: -4, pct: 68, label: "4/6" }, { id: -5, pct: 85, label: "5/6" }, { id: -6, pct: 100, label: "6/6" },
      { id: -7, pct: 78, label: "7/9" }, { id: -8, pct: 92, label: "11/12" },
    ];
  }, [submissions]);

  const loadData = async () => {
    setLoading(true);
    setError("");
    setHistoryError("");
    setDiscussionError("");
    try {
      const [problemData, detailsData, testcaseData] = await Promise.all([
        getProblem(problemId),
        getProblemDetails(problemId),
        getProblemTestcases(problemId),
      ]);
      setProblem(problemData);
      setDetails(detailsData);
      setTestcases(testcaseData);

      try {
        setSubmissions(await listMyProblemSubmissions(problemId));
      } catch (err) {
        setSubmissions([]);
        setHistoryError(err instanceof Error ? err.message : "Could not load submission history.");
      }
      try {
        setDiscussions(await listProblemDiscussions(problemId));
      } catch (err) {
        setDiscussions([]);
        setDiscussionError(err instanceof Error ? err.message : "Could not load discussions.");
      }
    } catch (err) {
      setProblem(null);
      setDetails(null);
      setError(err instanceof Error ? err.message : "Problem unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!Number.isFinite(problemId) || problemId <= 0) {
      setLoading(false);
      setError("Invalid problem id.");
      return;
    }
    loadData();
  }, [problemId]);

  const onCanvasMouseMove = (event: React.MouseEvent<HTMLDivElement>) => {
    if (dragNodeId === null) return;
    const container = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - container.left - dragOffset.current.x;
    const y = event.clientY - container.top - dragOffset.current.y;
    setDiagramNodes((prev) => prev.map((node) => (node.id === dragNodeId ? { ...node, x: Math.max(0, x), y: Math.max(0, y) } : node)));
  };

  const onCanvasMouseUp = () => setDragNodeId(null);

  const addDiagramNode = () => {
    const nextId = diagramNodes.length ? Math.max(...diagramNodes.map((node) => node.id)) + 1 : 1;
    setDiagramNodes((prev) => [...prev, { id: nextId, label: diagramTool, x: 40 + (nextId % 5) * 130, y: 60 + (nextId % 4) * 80 }]);
  };

  const handleLanguageChange = (next: Language) => {
    setLanguage(next);
    setCode(LANGUAGE_TEMPLATES[next]);
  };

  const handleSubmit = async () => {
    setError("");
    if (language !== "python") {
      setError("Execution currently supports Python only. You can still draft answers in any language.");
      return;
    }
    setSubmitting(true);
    try {
      await submitSolution(problemId, code);
      await loadData();
      setActiveTab("history");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const handlePostDiscussion = async () => {
    if (!discussionDraft.trim()) return;
    setPostingDiscussion(true);
    setDiscussionError("");
    try {
      await createProblemDiscussion(problemId, discussionDraft.trim());
      setDiscussionDraft("");
      setDiscussions(await listProblemDiscussions(problemId));
    } catch (err) {
      setDiscussionError(err instanceof Error ? err.message : "Could not post discussion.");
    } finally {
      setPostingDiscussion(false);
    }
  };

  if (loading) return <main className="page-shell panel">Loading workspace...</main>;
  if (!problem || !details) {
    return (
      <main className="page-shell panel">
        <h1>Problem unavailable</h1>
        <p className="error">{error || "Problem not found."}</p>
        <Link href="/problems" className="btn secondary">Back to problems</Link>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <div className="workspace-shell">
        <section className="workspace-pane">
          <header className="workspace-header">
            <div className="hero" style={{ marginBottom: 0 }}>
              <div>
                <h1 style={{ marginBottom: 4 }}>{problem.title}</h1>
                <p>{details.problem_type === "system_design" ? "System Design" : "Coding"} • {problem.difficulty} • {problem.tags?.join(", ") || "General"}</p>
              </div>
              <Link href="/problems" className="btn secondary">All problems</Link>
            </div>
          </header>
          <div className="workspace-body">
            <div className="tabs">
              {(["description", "examples", "constraints", "answer", "diagram", "discussions", "history", "analytics"] as TabKey[]).map((tab) => (
                <button key={tab} className={`tab-btn ${activeTab === tab ? "active" : ""}`} onClick={() => setActiveTab(tab)}>
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>

            {activeTab === "description" ? (
              <>
                <h2 style={{ marginTop: 0 }}>Problem Statement</h2>
                <p>{problem.description}</p>
                <p><strong>Language support:</strong> {details.supported_languages.join(", ")}</p>
              </>
            ) : null}

            {activeTab === "examples" ? (
              <>
                <h2 style={{ marginTop: 0 }}>Examples</h2>
                <div className="stack">
                  {(details.examples.length ? details.examples : testcases.map((t) => ({ input: t.input_data, output: t.expected_output }))).slice(0, 5).map((example, idx) => (
                    <div className="discussion-card" key={`${example.input}-${idx}`}>
                      <p><strong>Example {idx + 1} Input:</strong> {example.input}</p>
                      <p style={{ marginBottom: 0 }}><strong>Output:</strong> {example.output}</p>
                    </div>
                  ))}
                </div>
              </>
            ) : null}

            {activeTab === "constraints" ? (
              <>
                <h2 style={{ marginTop: 0 }}>Constraints</h2>
                <ul>{details.constraints.map((constraint) => <li key={constraint}>{constraint}</li>)}</ul>
                <h3>Functional Requirements</h3>
                <ul>{details.requirements.functional.map((req) => <li key={req}>{req}</li>)}</ul>
                <h3>Non-Functional Requirements</h3>
                <ul>{details.requirements.non_functional.map((req) => <li key={req}>{req}</li>)}</ul>
              </>
            ) : null}

            {activeTab === "answer" ? (
              <>
                <h2 style={{ marginTop: 0 }}>Answer Key / Guide</h2>
                <p>{details.answer_key.approach}</p>
                {details.answer_key.high_level_components?.length ? (
                  <>
                    <h3>Core Components</h3>
                    <ul>{details.answer_key.high_level_components.map((item) => <li key={item}>{item}</li>)}</ul>
                  </>
                ) : null}
                {details.answer_key.patterns?.length ? (
                  <>
                    <h3>Recommended Patterns</h3>
                    <ul>{details.answer_key.patterns.map((item) => <li key={item}>{item}</li>)}</ul>
                  </>
                ) : null}
                {details.answer_key.tradeoffs?.length ? (
                  <>
                    <h3>Trade-offs</h3>
                    <ul>{details.answer_key.tradeoffs.map((item) => <li key={item}>{item}</li>)}</ul>
                  </>
                ) : null}
                {details.answer_key.complexity_target ? <p><strong>Complexity target:</strong> {details.answer_key.complexity_target}</p> : null}
              </>
            ) : null}

            {activeTab === "diagram" ? (
              <>
                <h2 style={{ marginTop: 0 }}>Design Diagram Board</h2>
                <p>Choose component tools and build your architecture diagram interactively.</p>
                <div className="btn-row" style={{ marginBottom: 8 }}>
                  <select className="lang-select" value={diagramTool} onChange={(e) => setDiagramTool(e.target.value)}>
                    {(details.diagram_tools.length ? details.diagram_tools : ["Client", "Service", "Database", "Cache", "Queue"]).map((tool) => (
                      <option key={tool} value={tool}>{tool}</option>
                    ))}
                  </select>
                  <button className="btn" onClick={addDiagramNode}>Add Node</button>
                </div>
                <div
                  style={{
                    border: "1px dashed var(--border)",
                    borderRadius: 12,
                    minHeight: 320,
                    position: "relative",
                    background: "linear-gradient(180deg,#ffffff,#f9fafb)",
                    overflow: "hidden",
                  }}
                  onMouseMove={onCanvasMouseMove}
                  onMouseUp={onCanvasMouseUp}
                  onMouseLeave={onCanvasMouseUp}
                >
                  {diagramNodes.map((node) => (
                    <div
                      key={node.id}
                      onMouseDown={(event) => {
                        const target = event.currentTarget.getBoundingClientRect();
                        dragOffset.current = { x: event.clientX - target.left, y: event.clientY - target.top };
                        setDragNodeId(node.id);
                      }}
                      style={{
                        position: "absolute",
                        left: node.x,
                        top: node.y,
                        minWidth: 110,
                        padding: "0.45rem 0.55rem",
                        borderRadius: 10,
                        border: "1px solid #7dd3fc",
                        background: "#e0f2fe",
                        cursor: "grab",
                        fontWeight: 600,
                        userSelect: "none",
                      }}
                    >
                      {node.label}
                    </div>
                  ))}
                </div>
              </>
            ) : null}

            {activeTab === "discussions" ? (
              <>
                <h2 style={{ marginTop: 0 }}>Discussions</h2>
                <textarea value={discussionDraft} onChange={(e) => setDiscussionDraft(e.target.value)} placeholder="Share your approach or architecture rationale..." />
                <div className="btn-row" style={{ marginTop: 8 }}>
                  <button className="btn" onClick={handlePostDiscussion} disabled={postingDiscussion || !discussionDraft.trim()}>
                    {postingDiscussion ? "Posting..." : "Post"}
                  </button>
                </div>
                {discussionError ? <p className="error">{discussionError}</p> : null}
                <div className="stack" style={{ marginTop: 10 }}>
                  {mergedDiscussions.map((discussion) => (
                    <div className="discussion-card" key={discussion.id}>
                      <p style={{ marginTop: 0, marginBottom: 4 }}>
                        <strong>{discussion.username}</strong> • {new Date(discussion.created_at).toLocaleString()}
                      </p>
                      <p style={{ margin: 0 }}>{discussion.content}</p>
                    </div>
                  ))}
                </div>
              </>
            ) : null}

            {activeTab === "history" ? (
              <>
                <h2 style={{ marginTop: 0 }}>Submission History</h2>
                {historyError ? <p className="error">{historyError}</p> : null}
                {!historyError && submissions.length === 0 ? <p>No submissions yet.</p> : null}
                <div className="stack">
                  {submissions.map((submission) => {
                    const parsed = parseSubmissionResult(submission.result);
                    const passed = parsed.passed_test_cases ?? (submission.status === "accepted" ? 1 : 0);
                    const total = parsed.total_test_cases ?? 1;
                    return (
                      <div className="discussion-card" key={submission.id}>
                        <p><strong>Status:</strong> {submission.status}</p>
                        <p><strong>Test Cases:</strong> {passed}/{total}</p>
                        <p style={{ marginBottom: 0 }}><strong>Submitted:</strong> {new Date(submission.created_at).toLocaleString()}</p>
                      </div>
                    );
                  })}
                </div>
              </>
            ) : null}

            {activeTab === "analytics" ? (
              <>
                <h2 style={{ marginTop: 0 }}>Graph Analytics</h2>
                <div className="analytics-bars">
                  {analytics.map((point) => (
                    <div key={point.id} className="analytics-bar" style={{ height: `${point.pct}%` }} title={point.label} />
                  ))}
                </div>
                <p style={{ color: "var(--muted)" }}>Submission quality trend (real + enriched dummy starter data).</p>
              </>
            ) : null}
          </div>
        </section>

        <section className="workspace-pane">
          <header className="workspace-header">
            <h2 style={{ margin: 0 }}>Code Editor</h2>
            <p style={{ marginTop: 6, marginBottom: 0, color: "var(--muted)" }}>
              You can switch language while coding; runtime execution currently supports Python.
            </p>
          </header>
          <div className="workspace-body">
            <div className="btn-row" style={{ marginBottom: 10 }}>
              <select value={language} className="lang-select" onChange={(e) => handleLanguageChange(e.target.value as Language)}>
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="java">Java</option>
                <option value="cpp">C++</option>
              </select>
            </div>
            <textarea value={code} onChange={(e) => setCode(e.target.value)} style={{ minHeight: 460, fontFamily: "var(--font-mono), monospace" }} />
            <div className="btn-row" style={{ marginTop: 10 }}>
              <button className="btn" onClick={handleSubmit} disabled={submitting || !code.trim()}>
                {submitting ? "Submitting..." : "Submit"}
              </button>
            </div>
            {error ? <p className="error">{error}</p> : null}
          </div>
        </section>
      </div>
    </main>
  );
}
