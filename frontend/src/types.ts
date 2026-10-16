/** Shared types mirroring the FastAPI response models. */

export interface BulletRewrite {
  original: string;
  rewritten: string;
  rationale: string;
}

export interface Gap {
  title: string;
  detail: string;
}

export interface AnalysisResult {
  match_score: number;
  missing_keywords: string[];
  gaps: Gap[];
  bullet_rewrites: BulletRewrite[];
  provider: string;
  evidence_chunks: string[];
}

export interface ResumeUploadResult {
  filename: string;
  text: string;
  char_count: number;
}

export interface HealthResult {
  status: string;
  llm_provider: string;
  embedder: string;
  vector_store: string;
}

export type Step = "upload" | "job" | "results";
