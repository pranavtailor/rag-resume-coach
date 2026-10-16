/** Thin typed client for the FastAPI backend (served via the Vite /api proxy). */

import type { AnalysisResult, HealthResult, ResumeUploadResult } from "./types";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* fall through with the generic message */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export async function uploadResume(file: File): Promise<ResumeUploadResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/resume", { method: "POST", body: form });
  return handleResponse<ResumeUploadResult>(res);
}

export async function analyzeResume(
  resumeText: string,
  jobText: string,
): Promise<AnalysisResult> {
  const res = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume_text: resumeText, job_text: jobText }),
  });
  return handleResponse<AnalysisResult>(res);
}

export async function getHealth(): Promise<HealthResult> {
  const res = await fetch("/api/health");
  return handleResponse<HealthResult>(res);
}
