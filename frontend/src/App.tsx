import { useState } from "react";
import { analyzeResume } from "./api";
import JobPostingInput from "./components/JobPostingInput";
import ResultsView from "./components/ResultsView";
import ResumeUpload from "./components/ResumeUpload";
import type { AnalysisResult, Step } from "./types";

const STEPS: { id: Step; label: string }[] = [
  { id: "upload", label: "Résumé" },
  { id: "job", label: "Job posting" },
  { id: "results", label: "Analysis" },
];

export default function App() {
  const [step, setStep] = useState<Step>("upload");
  const [resumeText, setResumeText] = useState("");
  const [jobText, setJobText] = useState("");
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stepIndex = STEPS.findIndex((s) => s.id === step);

  // Takes the job text as an argument (rather than reading state) because
  // setJobText is async and we need the fresh value for the API call.
  async function handleAnalyze(text: string) {
    setJobText(text);
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeResume(resumeText, text);
      setAnalysis(result);
      setStep("results");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  function restart() {
    setStep("upload");
    setResumeText("");
    setJobText("");
    setAnalysis(null);
    setError(null);
  }

  return (
    <div className="page">
      <header className="hero">
        <h1>
          RAG Résumé Coach <span className="badge">demo</span>
        </h1>
        <p className="subtitle">
          Upload your résumé, paste a job posting, and get a retrieval-grounded
          gap analysis with tailored bullet rewrites.
        </p>
      </header>

      <ol className="stepper">
        {STEPS.map((s, i) => (
          <li
            key={s.id}
            className={i < stepIndex ? "done" : i === stepIndex ? "active" : ""}
          >
            <span className="step-dot">{i + 1}</span> {s.label}
          </li>
        ))}
      </ol>

      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}

      <main className="card">
        {step === "upload" && (
          <ResumeUpload
            initialText={resumeText}
            onComplete={(text) => {
              setResumeText(text);
              setStep("job");
            }}
          />
        )}

        {step === "job" && (
          <JobPostingInput
            initialText={jobText}
            loading={loading}
            onBack={() => setStep("upload")}
            onAnalyze={handleAnalyze}
          />
        )}

        {step === "results" && analysis && (
          <ResultsView analysis={analysis} onRestart={restart} />
        )}
      </main>

      <footer className="footer">
        Local-first RAG: résumé text never leaves your machine unless you
        configure an LLM API key.
      </footer>
    </div>
  );
}
