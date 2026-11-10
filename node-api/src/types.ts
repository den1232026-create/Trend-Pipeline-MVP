/** Types aligned with shared/contracts.md (+ Job.mocked). */

export type TrendStage = "emerging" | "rising" | "peak";
export type TrendType = "face-swap" | "template-meme" | "ai-visual" | "other";

export interface Reference {
  url: string;
  title: string;
  score: number;
  created_utc: number;
}

export interface TrendSignals {
  score?: number | null;
  num_comments?: number | null;
  upvote_ratio?: number | null;
  rising_rank?: number | null;
  upvote_velocity?: number | null;
}

export interface Trend {
  id: string;
  title: string;
  summary: string;
  source: "reddit";
  references: Reference[];
  signals: TrendSignals;
  stage: TrendStage;
  trend_type: TrendType;
  why_trending: string;
  llm_brief: string | null;
}

export interface UserInput {
  name: string;
  type: "image" | "text";
  required: boolean;
}

export interface PresetStep {
  model: string;
  prompt: string;
  params: Record<string, unknown>;
}

export interface Preset {
  id: string;
  trend_id: string;
  title: string;
  user_inputs: UserInput[];
  steps: PresetStep[];
  output_type: "image";
  est_cost_rub: number;
  pipeline_rationale: string;
}

export type JobStatus = "queued" | "running" | "done" | "error";

export interface Job {
  id: string;
  preset_id: string;
  status: JobStatus;
  input_paths: Record<string, string>;
  output_path: string | null;
  error: string | null;
  mocked: boolean;
}

export interface ApiErrorBody {
  error: string;
  detail?: string;
}
