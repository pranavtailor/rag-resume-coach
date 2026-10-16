import { useState } from "react";

interface Props {
  initialText: string;
  loading: boolean;
  onBack: () => void;
  onAnalyze: (text: string) => void;
}

export default function JobPostingInput({
  initialText,
  loading,
  onBack,
  onAnalyze,
}: Props) {
  const [text, setText] = useState(initialText);
  const valid = text.trim().length >= 50;

  return (
    <div>
      <h2>2. Paste the job posting</h2>
      <p className="muted">
        Paste the full job description — requirements, responsibilities, and
        preferred qualifications all help the analysis.
      </p>

      <label className="field-label" htmlFor="job-text">
        Job posting
      </label>
      <textarea
        id="job-text"
        className="textarea"
        rows={14}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste the job posting here…"
      />
      {!valid && text.length > 0 && (
        <p className="hint">A bit more detail helps — at least a few sentences.</p>
      )}

      <div className="actions">
        <button className="btn" onClick={onBack} disabled={loading}>
          ← Back
        </button>
        <button
          className="btn primary"
          disabled={!valid || loading}
          onClick={() => onAnalyze(text.trim())}
        >
          {loading ? "Analyzing…" : "Analyze match"}
        </button>
      </div>
    </div>
  );
}
