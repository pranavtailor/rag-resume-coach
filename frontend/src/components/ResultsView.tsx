import type { AnalysisResult } from "../types";

interface Props {
  analysis: AnalysisResult;
  onRestart: () => void;
}

/** Circular score gauge rendered with SVG. */
function ScoreRing({ score }: { score: number }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const filled = (Math.min(100, Math.max(0, score)) / 100) * circumference;
  const color =
    score >= 70 ? "var(--green)" : score >= 40 ? "var(--amber)" : "var(--red)";

  return (
    <div className="score-wrap">
      <svg width="140" height="140" viewBox="0 0 140 140" role="img"
           aria-label={`Match score ${Math.round(score)} out of 100`}>
        <circle cx="70" cy="70" r={radius} fill="none"
                stroke="var(--ring-bg)" strokeWidth="12" />
        <circle
          cx="70" cy="70" r={radius} fill="none"
          stroke={color} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
          transform="rotate(-90 70 70)"
        />
        <text x="70" y="66" textAnchor="middle" className="score-number">
          {Math.round(score)}
        </text>
        <text x="70" y="88" textAnchor="middle" className="score-label">
          / 100
        </text>
      </svg>
      <p className="muted small">overall match</p>
    </div>
  );
}

export default function ResultsView({ analysis, onRestart }: Props) {
  const isDemo = analysis.provider.toLowerCase().includes("stub");

  return (
    <div>
      <div className="results-header">
        <h2>3. Your analysis</h2>
        <span className={`provider-badge${isDemo ? " demo" : ""}`}>
          {isDemo ? "heuristic demo mode" : `powered by ${analysis.provider}`}
        </span>
      </div>

      {isDemo && (
        <p className="muted small demo-note">
          Demo mode uses keyword heuristics, not an LLM. Set{" "}
          <code>OPENAI_API_KEY</code> in the backend <code>.env</code> for
          full AI-powered analysis.
        </p>
      )}

      <div className="results-grid">
        <ScoreRing score={analysis.match_score} />

        <section className="panel">
          <h3>Missing keywords</h3>
          {analysis.missing_keywords.length === 0 ? (
            <p className="muted">None — strong keyword coverage.</p>
          ) : (
            <div className="chips">
              {analysis.missing_keywords.map((kw) => (
                <span key={kw} className="chip warn">
                  {kw}
                </span>
              ))}
            </div>
          )}
        </section>
      </div>

      <section className="panel">
        <h3>Gaps to address</h3>
        {analysis.gaps.length === 0 ? (
          <p className="muted">No major gaps detected.</p>
        ) : (
          <ul className="gap-list">
            {analysis.gaps.map((gap) => (
              <li key={gap.title}>
                <strong>{gap.title}</strong>
                <p>{gap.detail}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h3>Suggested bullet rewrites</h3>
        {analysis.bullet_rewrites.length === 0 ? (
          <p className="muted">Nothing to rewrite — bullets look strong.</p>
        ) : (
          <div className="rewrites">
            {analysis.bullet_rewrites.map((rw, i) => (
              <article key={i} className="rewrite">
                <div className="rewrite-side before">
                  <span className="rewrite-tag">Before</span>
                  <p>{rw.original}</p>
                </div>
                <div className="rewrite-arrow" aria-hidden="true">→</div>
                <div className="rewrite-side after">
                  <span className="rewrite-tag">After</span>
                  <p>{rw.rewritten}</p>
                </div>
                <p className="rationale">
                  <strong>Why:</strong> {rw.rationale}
                </p>
              </article>
            ))}
          </div>
        )}
      </section>

      {analysis.evidence_chunks.length > 0 && (
        <details className="evidence">
          <summary>
            Retrieved evidence ({analysis.evidence_chunks.length} chunks)
          </summary>
          <ul>
            {analysis.evidence_chunks.map((chunk, i) => (
              <li key={i}>{chunk}</li>
            ))}
          </ul>
        </details>
      )}

      <div className="actions">
        <button className="btn" onClick={onRestart}>
          ↺ Start over
        </button>
      </div>
    </div>
  );
}
