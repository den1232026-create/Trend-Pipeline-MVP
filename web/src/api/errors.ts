import { ApiError } from "./client";
import type { MessageKey } from "../i18n/locales";

type Translate = (key: MessageKey) => string;

/** Normalize BFF / FastAPI error bodies into a short UI string. */
export function formatApiError(
  err: unknown,
  fallback = "Request failed",
  t?: Translate
): string {
  const requestFailed = t?.("requestFailed") ?? fallback;
  if (err instanceof ApiError) {
    const body = err.body as { error?: string; detail?: unknown } | null;
    const detail = formatDetail(body?.detail);
    if (body?.error === "python_unavailable") {
      if (detail) {
        const prefix = t?.("pythonUnavailableDetail") ?? "Python API unavailable";
        return `${prefix} (${detail})`;
      }
      return t?.("pythonUnavailable") ?? "Python API unavailable — start uvicorn on :8000";
    }
    if (detail) return detail;
    if (body?.error) return body.error;
    return err.message || `HTTP ${err.status}`;
  }
  if (err instanceof Error) return err.message || requestFailed;
  return requestFailed;
}

function formatDetail(detail: unknown): string | null {
  if (detail == null) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return JSON.stringify(item);
      })
      .filter(Boolean);
    return parts.length ? parts.join("; ") : null;
  }
  if (typeof detail === "object") return JSON.stringify(detail);
  return String(detail);
}
