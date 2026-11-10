import type { HealthResponse, Job, Preset, Trend } from "../types/contracts";
import fixtureTrend from "../fixtures/trend.json";
import fixturePreset from "../fixtures/preset.json";
import fixtureJob from "../fixtures/job.json";

const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES === "1";
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function parseJson(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function briefErrorMessage(body: unknown, status: number): string {
  const errObj = body as { error?: string; detail?: unknown } | null;
  const detail = errObj?.detail;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) =>
        typeof item === "string"
          ? item
          : item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : null
      )
      .filter(Boolean)
      .join("; ");
  }
  if (errObj?.error) return errObj.error;
  return `HTTP ${status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    throw new ApiError(`Network error: ${detail}`, 0, {
      error: "network_error",
      detail,
    });
  }
  const body = await parseJson(res);
  if (!res.ok) {
    throw new ApiError(briefErrorMessage(body, res.status), res.status, body);
  }
  return body as T;
}

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export async function getHealth(): Promise<HealthResponse> {
  if (USE_FIXTURES) return { ok: true, mock_generate: true };
  return request<HealthResponse>("/health");
}

export async function listTrends(): Promise<Trend[]> {
  if (USE_FIXTURES) return [fixtureTrend as Trend];
  const data = await request<Trend[] | { trends: Trend[] }>("/trends");
  return Array.isArray(data) ? data : data.trends ?? [];
}

export async function getTrend(id: string): Promise<Trend> {
  if (USE_FIXTURES) {
    const t = fixtureTrend as Trend;
    if (t.id !== id) throw new ApiError("trend_not_found", 404, { error: "not_found" });
    return t;
  }
  return request<Trend>(`/trends/${encodeURIComponent(id)}`);
}

export async function refreshTrends(): Promise<unknown> {
  if (USE_FIXTURES) {
    await delay(300);
    return { ok: true, count: 1 };
  }
  return request("/trends/refresh", { method: "POST" });
}

export async function buildPreset(trendId: string): Promise<Preset> {
  if (USE_FIXTURES) {
    await delay(400);
    return {
      ...(fixturePreset as Preset),
      trend_id: trendId,
      id: `preset_${trendId}`,
    };
  }
  return request<Preset>(`/trends/${encodeURIComponent(trendId)}/build-preset`, {
    method: "POST",
  });
}

export async function listPresets(): Promise<Preset[]> {
  if (USE_FIXTURES) return [fixturePreset as Preset];
  const data = await request<Preset[] | { presets: Preset[] }>("/presets");
  return Array.isArray(data) ? data : data.presets ?? [];
}

export async function getPreset(id: string): Promise<Preset> {
  if (USE_FIXTURES) return fixturePreset as Preset;
  return request<Preset>(`/presets/${encodeURIComponent(id)}`);
}

export async function findPresetForTrend(trendId: string): Promise<Preset | null> {
  const presets = await listPresets();
  return presets.find((p) => p.trend_id === trendId) ?? null;
}

export async function generate(presetId: string, face: File): Promise<Job> {
  if (USE_FIXTURES) {
    await delay(500);
    return {
      ...(fixtureJob as Job),
      id: `job_fixture_${Date.now()}`,
      preset_id: presetId,
      status: "done",
      mocked: true,
      output_path: (fixtureJob as Job).output_path,
    };
  }
  const form = new FormData();
  form.append("face", face);
  form.append("preset_id", presetId);
  return request<Job>("/generate", { method: "POST", body: form });
}

export async function getJob(id: string): Promise<Job> {
  if (USE_FIXTURES) {
    return { ...(fixtureJob as Job), id, status: "done", mocked: true };
  }
  return request<Job>(`/jobs/${encodeURIComponent(id)}`);
}

/** Poll every 1.5s until done/error (orchestrator brief). */
export async function pollJob(
  id: string,
  onUpdate?: (job: Job) => void,
  signal?: AbortSignal
): Promise<Job> {
  for (;;) {
    if (signal?.aborted) throw new Error("aborted");
    const job = await getJob(id);
    onUpdate?.(job);
    if (job.status === "done" || job.status === "error") return job;
    await delay(1500);
  }
}

export function artifactUrl(outputPath: string): string {
  const name = outputPath.split(/[/\\]/).pop() || outputPath;
  return `${API_BASE}/artifacts/${encodeURIComponent(name)}`;
}

/** Prefer local artifact; fall back to CDN URL from job.output_url. */
export function jobResultImageUrl(job: Job): string | null {
  if (job.output_path) return artifactUrl(job.output_path);
  if (job.output_url) return job.output_url;
  return null;
}

export function fixturesEnabled(): boolean {
  return USE_FIXTURES;
}
