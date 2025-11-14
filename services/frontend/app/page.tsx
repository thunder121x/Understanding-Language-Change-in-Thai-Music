'use client';

import { useMemo, useState } from "react";

type Prediction = {
  era: string;
  genre: string;
  eraConfidence: number;
  genreConfidence: number;
  overallConfidence: number;
};

const ERA_OPTIONS = ["1990–1999", "2000–2009", "2010–2019", "2020–2025"];
const GENRE_OPTIONS = ["Pop", "Rock", "Indie", "Hip-hop"];
const MODEL_NOTE = "ไม่รู้จะเขียนอะไรดี ทำๆไว้ก่อน";

export default function Home() {
  const [lyrics, setLyrics] = useState("");
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const lyricLength = useMemo(() => lyrics.trim().length, [lyrics]);

  function randomPrediction(): Prediction {
    const eraConfidence = Math.round(Math.random() * 25);
    const genreConfidence = Math.round(Math.random() * 30);
    const overallConfidence = Math.round(
      (eraConfidence + genreConfidence) / 2
    );

    return {
      era: ERA_OPTIONS[Math.floor(Math.random() * ERA_OPTIONS.length)],
      genre: GENRE_OPTIONS[Math.floor(Math.random() * GENRE_OPTIONS.length)],
      eraConfidence,
      genreConfidence,
      overallConfidence
    };
  }

  async function handleClassify() {
    if (!lyrics.trim()) {
      setError("Please write on lyrics first.");
      alert("Please write on lyrics first.");
      return;
    }

    setLoading(true);
    setError(null);

    // Simulate a lightweight async action so the UI feels responsive.
    await new Promise((resolve) => setTimeout(resolve, 400));
    setPrediction(randomPrediction());
    setLoading(false);
  }

  return (
    <div className="page">
      <header>
        <div className="logo">Dummy web logo</div>
      </header>

      <main>
        <section className="panel">
          <h2 className="panel-title">Paste lyrics</h2>
          <p className="panel-subtitle">
            Add Song lyrics on the left, then classify to see the predicted era
            and genre.
          </p>

          <textarea
            id="lyricsInput"
            placeholder="Add song lyrics here..."
            value={lyrics}
            onChange={(event) => setLyrics(event.target.value)}
            disabled={loading}
          />

          <div className="input-actions">
            <span className="status">
              {lyricLength > 0
                ? `${lyricLength.toLocaleString()} characters`
                : "No lyrics yet"}
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button
                className="btn btn-primary"
                type="button"
                id="btnClassify"
                onClick={handleClassify}
                disabled={loading}
              >
                {loading ? "Classifying..." : "Classify from lyrics"}
              </button>
            </div>
          </div>
        </section>

        <section className="panel" id="resultPanel">
          {!prediction ? (
            <div className="placeholder-center" id="placeholder">
              <div className="placeholder-title">
                Add lyrics to begin analysis
              </div>
              <div className="muted">
                Predictions for song <strong>era</strong> and{" "}
                <strong>genre</strong> will appear here.
              </div>
            </div>
          ) : (
            <div id="resultContent">
              <div className="result-header">
                <div>
                  <div className="big-number" id="confidenceText">
                    {prediction.overallConfidence}%
                  </div>
                  <div className="muted">overall confidence</div>
                </div>
                <div className="muted" id="modelNote">
                  {MODEL_NOTE}
                </div>
              </div>

              <div className="tag-row">
                <span className="tag">
                  Era: <span id="eraTag">{prediction.era}</span>
                </span>
                <span className="tag">
                  Genre: <span id="genreTag">{prediction.genre}</span>
                </span>
              </div>

              <div className="meter-group">
                <div className="meter-label">
                  <span>Era confidence</span>
                  <span id="eraPctLabel">{prediction.eraConfidence}%</span>
                </div>
                <div className="meter">
                  <div
                    className="meter-fill"
                    id="eraMeter"
                    style={{ width: `${prediction.eraConfidence}%` }}
                  />
                </div>

                <div className="meter-label">
                  <span>Genre confidence</span>
                  <span id="genrePctLabel">{prediction.genreConfidence}%</span>
                </div>
                <div className="meter">
                  <div
                    className="meter-fill"
                    id="genreMeter"
                    style={{ width: `${prediction.genreConfidence}%` }}
                  />
                </div>
              </div>

              <div className="muted" style={{ marginTop: 10, fontSize: 11 }}>
                This is placeholder output for design. Later you&apos;ll replace
                it with real predictions from your ML API.
              </div>
            </div>
          )}

          <div id="error" className="error">
            {error}
          </div>
        </section>
      </main>
    </div>
  );
}
