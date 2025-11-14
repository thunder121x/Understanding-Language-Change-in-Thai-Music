'use client';

import { useState } from "react";
import { ResultPanel } from "../components/ResultPanel";

export default function Home() {
  const [text, setText] = useState("");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!process.env.NEXT_PUBLIC_API_URL) {
      setError("NEXT_PUBLIC_API_URL is not configured.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });

      if (!res.ok) {
        throw new Error(`Request failed with ${res.status}`);
      }

      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Song Era Classifier</h1>
      <p>Paste Thai lyrics and get an estimated musical era.</p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="ใจสลายเหมือนเพลงยุค 90..."
      />
      <button onClick={submit} disabled={loading}>
        {loading ? "Predicting..." : "Predict"}
      </button>
      {error && <p style={{ color: "#f87171" }}>{error}</p>}
      <ResultPanel content={result} />
    </main>
  );
}
