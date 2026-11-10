import type { Request, Response } from "express";

const PYTHON_UNAVAILABLE = "python_unavailable";

export function pythonBaseUrl(): string {
  return (process.env.PYTHON_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
}

/** Map BFF /api/... → Python /... */
export function toPythonPath(apiPath: string): string {
  const stripped = apiPath.replace(/^\/api/, "") || "/";
  return stripped.startsWith("/") ? stripped : `/${stripped}`;
}

export async function proxyJson(
  req: Request,
  res: Response,
  opts?: { method?: string; pathOverride?: string; body?: BodyInit | null; headers?: Record<string, string> }
): Promise<void> {
  const method = opts?.method || req.method;
  const path = opts?.pathOverride || toPythonPath(req.originalUrl.split("?")[0]);
  const url = `${pythonBaseUrl()}${path}${req.url.includes("?") ? req.url.slice(req.url.indexOf("?")) : ""}`;

  const headers: Record<string, string> = { ...(opts?.headers || {}) };
  if (opts?.body !== undefined && !headers["Content-Type"] && typeof opts.body === "string") {
    headers["Content-Type"] = "application/json";
  }

  try {
    const upstream = await fetch(url, {
      method,
      headers,
      body: opts?.body === undefined ? undefined : opts.body,
    });

    const contentType = upstream.headers.get("content-type") || "application/json";
    const buf = Buffer.from(await upstream.arrayBuffer());
    res.status(upstream.status);
    res.setHeader("Content-Type", contentType);
    res.send(buf);
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    res.status(502).json({ error: PYTHON_UNAVAILABLE, detail });
  }
}

export async function proxyMultipartGenerate(req: Request, res: Response): Promise<void> {
  const file = req.file;
  const presetId = typeof req.body?.preset_id === "string" ? req.body.preset_id : "";

  if (!file) {
    res.status(400).json({ error: "missing_face", detail: "multipart field 'face' required" });
    return;
  }
  if (!presetId) {
    res.status(400).json({ error: "missing_preset_id", detail: "form field 'preset_id' required" });
    return;
  }

  const form = new FormData();
  const blob = new Blob([new Uint8Array(file.buffer)], {
    type: file.mimetype || "application/octet-stream",
  });
  form.append("face", blob, file.originalname || "face.png");
  form.append("preset_id", presetId);

  try {
    const upstream = await fetch(`${pythonBaseUrl()}/generate`, {
      method: "POST",
      body: form,
    });
    const contentType = upstream.headers.get("content-type") || "application/json";
    const buf = Buffer.from(await upstream.arrayBuffer());
    res.status(upstream.status);
    res.setHeader("Content-Type", contentType);
    res.send(buf);
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    res.status(502).json({ error: PYTHON_UNAVAILABLE, detail });
  }
}
