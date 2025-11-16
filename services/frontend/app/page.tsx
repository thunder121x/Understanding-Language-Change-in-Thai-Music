'use client';

import { useMemo, useState } from "react";

type Prediction = {
  era: string;
  genre: string;
  eraConfidence: number;
  genreConfidence: number;
  overallConfidence: number;
};

type ApiPrediction = Record<string, unknown>;
type ApiScores = Record<string, number>;

const MODEL_NOTE = "ไม่รู้จะเขียนอะไรดี ทำๆไว้ก่อน";
const DEFAULT_PREDICTION: Prediction = {
  era: "Unknown era",
  genre: "Unknown genre",
  eraConfidence: 0,
  genreConfidence: 0,
  overallConfidence: 0
};

function clampConfidence(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function pickString(
  data: ApiPrediction,
  candidates: string[],
  fallback: string
): string {
  for (const key of candidates) {
    const value = data[key];
    if (typeof value === "string" && value.trim().length > 0) {
      return value;
    }
  }
  return fallback;
}

function pickConfidence(
  data: ApiPrediction,
  candidates: string[],
  fallback: number
): number {
  for (const key of candidates) {
    const value = data[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return clampConfidence(value);
    }
    if (typeof value === "string" && value.trim().length > 0) {
      const parsed = Number.parseFloat(value);
      if (Number.isFinite(parsed)) {
        return clampConfidence(parsed);
      }
    }
  }
  return fallback;
}

function mapApiPrediction(raw: ApiPrediction | null): Prediction {
  const data = raw && typeof raw === "object" ? (raw as ApiPrediction) : {};
  const era = pickString(
    data,
    ["era", "predicted_era", "predictedEra", "era_label"],
    DEFAULT_PREDICTION.era
  );
  const genre = pickString(
    data,
    ["genre", "predicted_genre", "predictedGenre", "genre_label"],
    DEFAULT_PREDICTION.genre
  );

  const eraConfidence = pickConfidence(
    data,
    ["era_confidence", "eraConfidence", "era_score"],
    DEFAULT_PREDICTION.eraConfidence
  );
  const genreConfidence = pickConfidence(
    data,
    ["genre_confidence", "genreConfidence", "genre_score"],
    DEFAULT_PREDICTION.genreConfidence
  );
  const overallConfidence = pickConfidence(
    data,
    ["overall_confidence", "overallConfidence", "confidence"],
    clampConfidence((eraConfidence + genreConfidence) / 2)
  );

  return {
    era,
    genre,
    eraConfidence,
    genreConfidence,
    overallConfidence
  };
}

export default function Home() {
  const [lyrics, setLyrics] = useState("");
  const [searchTitle, setSearchTitle] = useState("");
  const [searchArtist, setSearchArtist] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchMessage, setSearchMessage] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const lyricLength = useMemo(() => lyrics.trim().length, [lyrics]);

  async function handleSearchLyrics() {
    const trimmedTitle = searchTitle.trim();
    const trimmedArtist = searchArtist.trim();

    if (!trimmedTitle) {
      const message = "Please enter a song title to search.";
      setSearchMessage(message);
      alert(message);
      return;
    }

    if (!process.env.NEXT_PUBLIC_API_URL) {
      setSearchMessage("NEXT_PUBLIC_API_URL is not configured.");
      return;
    }

    const baseUrl = process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
    const params = new URLSearchParams({ title: trimmedTitle });
    if (trimmedArtist) params.set("artist", trimmedArtist);

    setSearching(true);
    setSearchMessage(null);
    setError(null);

    try {
      const response = await fetch(`${baseUrl}/api/search-lyrics?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`Search request failed with status ${response.status}`);
      }

      const data = (await response.json()) as Record<string, unknown>;
      const nextLyrics =
        typeof data["lyrics"] === "string" && data["lyrics"].trim().length > 0
          ? (data["lyrics"] as string)
          : "No lyrics found.";

      setLyrics(nextLyrics);
      setPrediction(null);
      setSearchMessage("Lyrics loaded from search result.");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Unable to fetch lyrics right now.";
      setSearchMessage(message);
    } finally {
      setSearching(false);
    }
  }

  async function handleClassify() {
    if (!lyrics.trim()) {
      const message = "Please write on lyrics first.";
      setError(message);
      alert(message);
      return;
    }

    if (!process.env.NEXT_PUBLIC_API_URL) {
      setError("NEXT_PUBLIC_API_URL is not configured.");
      return;
    }

    const baseUrl = process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
    setLoading(true);
    setError(null);
    setPrediction(null);

    try {
      const payload = JSON.stringify({ text: lyrics });

      const [genreResponse, eraResponse] = await Promise.all([
        fetch(`${baseUrl}/predict/genre`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload
        }),
        fetch(`${baseUrl}/predict/era`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload
        })
      ]);

      if (!genreResponse.ok) {
        throw new Error(
          `Genre request failed with status ${genreResponse.status}`
        );
      }
      if (!eraResponse.ok) {
        throw new Error(`Era request failed with status ${eraResponse.status}`);
      }

      const genreJson = (await genreResponse.json()) as ApiPrediction;
      const eraJson = (await eraResponse.json()) as ApiPrediction;

      const maxScore = (scores: unknown): number | null => {
        if (!scores || typeof scores !== "object") return null;
        const values = Object.values(scores as ApiScores).filter((v) =>
          Number.isFinite(v)
        ) as number[];
        if (!values.length) return null;
        return Math.max(...values);
      };

      const genreTop = maxScore(genreJson["scores"]);
      const eraTop = maxScore(eraJson["scores"]);

      const combined: ApiPrediction = {
        predicted_genre: genreJson["predicted_genre"],
        genre_confidence: genreTop ? genreTop * 100 : undefined,
        predicted_era: eraJson["predicted_era"],
        era_confidence: eraTop ? eraTop * 100 : undefined
      };

      setPrediction(mapApiPrediction(combined));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Unknown error occurred";
      setError(message);
      setPrediction(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header>
        <div className="logo">Dummy web logo</div>
      </header>

      <main>
        <section className="panel">
          <h2 className="panel-title">Search or paste lyrics</h2>
          <p className="panel-subtitle">
            Search by song title (artist optional) to auto-fill the lyrics box,
            or paste lyrics manually to classify era and genre.
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 12,
              background: "#f9fafb",
              border: "1px solid #e5e7eb",
              borderRadius: 12,
              padding: 12,
              marginBottom: 12
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label style={{ fontSize: 12, color: "#4b5563", fontWeight: 600 }}>
                Song title *
              </label>
              <input
                type="text"
                placeholder="e.g., Shape of You"
                value={searchTitle}
                onChange={(event) => setSearchTitle(event.target.value)}
                disabled={loading || searching}
                style={{
                  padding: "8px 10px",
                  borderRadius: 8,
                  border: "1px solid #d1d5db",
                  background: "#ffffff"
                }}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label style={{ fontSize: 12, color: "#4b5563", fontWeight: 600 }}>
                Artist (optional)
              </label>
              <input
                type="text"
                placeholder="e.g., Ed Sheeran"
                value={searchArtist}
                onChange={(event) => setSearchArtist(event.target.value)}
                disabled={loading || searching}
                style={{
                  padding: "8px 10px",
                  borderRadius: 8,
                  border: "1px solid #d1d5db",
                  background: "#ffffff"
                }}
              />
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "flex-end",
                justifyContent: "flex-start"
              }}
            >
              <button
                className="btn btn-primary"
                type="button"
                onClick={handleSearchLyrics}
                disabled={loading || searching}
                style={{ width: "100%", justifyContent: "center" }}
              >
                {searching ? "Searching..." : "Search lyrics"}
              </button>
            </div>
          </div>

          <div className="status" style={{ marginBottom: 8 }}>
            {searchMessage || "Use search to auto-fill lyrics, then classify."}
          </div>

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
                Predictions shown here are provided by the running FastAPI
                backend.
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
