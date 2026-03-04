"use client";

import Link from "next/link";
import { useState } from "react";
import { createProblem } from "../../lib/api";

type LocalTestcase = {
  input_data: string;
  expected_output: string;
  is_hidden: boolean;
};

export default function CreateProblemPage() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [difficulty, setDifficulty] = useState<"Easy" | "Medium" | "Hard">("Medium");
  const [tags, setTags] = useState("");
  const [testCases, setTestCases] = useState<LocalTestcase[]>([
    { input_data: "", expected_output: "", is_hidden: false },
  ]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const updateTestCase = (idx: number, patch: Partial<LocalTestcase>) => {
    setTestCases((prev) => prev.map((tc, i) => (i === idx ? { ...tc, ...patch } : tc)));
  };

  const addTestCase = () => {
    setTestCases((prev) => [...prev, { input_data: "", expected_output: "", is_hidden: true }]);
  };

  const removeTestCase = (idx: number) => {
    setTestCases((prev) => prev.filter((_, i) => i !== idx));
  };

  const handlePublish = async () => {
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const payload = {
        title,
        description,
        difficulty,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        test_cases: testCases.filter((tc) => tc.input_data.trim() && tc.expected_output.trim()),
      };
      const created = await createProblem(payload);
      setMessage(`Problem published with id ${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to publish problem");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page-shell panel">
      <div className="hero">
        <div>
          <h1>Create & Publish Problem</h1>
          <p>Add coding or system design prompts with visible/hidden test cases.</p>
        </div>
        <Link href="/" className="btn secondary">Dashboard</Link>
      </div>

      <div className="stack">
        <input
          className="field"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          className="field"
          style={{ minHeight: 140 }}
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <select value={difficulty} onChange={(e) => setDifficulty(e.target.value as "Easy" | "Medium" | "Hard")}>
          <option value="Easy">Easy</option>
          <option value="Medium">Medium</option>
          <option value="Hard">Hard</option>
        </select>
        <input
          className="field"
          placeholder="Tags (comma separated)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />
      </div>

      <h2>Test Cases</h2>
      {testCases.map((tc, idx) => (
        <div key={idx} className="panel" style={{ marginBottom: 8, padding: 12 }}>
          <input
            className="field"
            style={{ marginBottom: 6 }}
            placeholder="Input"
            value={tc.input_data}
            onChange={(e) => updateTestCase(idx, { input_data: e.target.value })}
          />
          <input
            className="field"
            style={{ marginBottom: 6 }}
            placeholder="Expected Output"
            value={tc.expected_output}
            onChange={(e) => updateTestCase(idx, { expected_output: e.target.value })}
          />
          <label>
            <input
              type="checkbox"
              checked={tc.is_hidden}
              onChange={(e) => updateTestCase(idx, { is_hidden: e.target.checked })}
            />{" "}
            Hidden testcase
          </label>
          <div style={{ marginTop: 8 }}>
            <button className="btn secondary" onClick={() => removeTestCase(idx)} disabled={testCases.length <= 1}>
              Remove
            </button>
          </div>
        </div>
      ))}
      <div className="btn-row">
        <button className="btn secondary" onClick={addTestCase}>Add testcase</button>
        <button className="btn" onClick={handlePublish} disabled={loading || !title.trim() || !description.trim()}>
          {loading ? "Publishing..." : "Publish Problem"}
        </button>
      </div>
      {message ? <p className="ok">{message}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </main>
  );
}
