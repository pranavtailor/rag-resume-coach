import { useRef, useState } from "react";
import { uploadResume } from "../api";

interface Props {
  initialText: string;
  onComplete: (text: string) => void;
}

const ACCEPT = ".pdf,.docx,.txt";

export default function ResumeUpload({ initialText, onComplete }: Props) {
  const [text, setText] = useState(initialText);
  const [filename, setFilename] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setUploading(true);
    setError(null);
    try {
      const result = await uploadResume(file);
      setText(result.text);
      setFilename(result.filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <h2>1. Upload your résumé</h2>
      <p className="muted">
        PDF, DOCX, or TXT. Text is extracted locally by the backend — you can
        edit it below before continuing.
      </p>

      <div
        className={`dropzone${dragging ? " dragging" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files?.[0];
          if (file) void handleFile(file);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
            e.target.value = "";
          }}
        />
        {uploading ? (
          <p>Extracting text…</p>
        ) : (
          <p>
            <strong>Drag &amp; drop</strong> your résumé here, or{" "}
            <span className="link">browse files</span>
          </p>
        )}
      </div>

      {error && (
        <div className="alert" role="alert">
          {error}
        </div>
      )}

      {filename && <p className="muted small">Parsed: {filename}</p>}

      <label className="field-label" htmlFor="resume-text">
        Résumé text
      </label>
      <textarea
        id="resume-text"
        className="textarea"
        rows={12}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="…or paste your résumé text directly here"
      />

      <div className="actions">
        <button
          className="btn primary"
          disabled={text.trim().length < 50}
          onClick={() => onComplete(text.trim())}
        >
          Continue →
        </button>
      </div>
    </div>
  );
}
